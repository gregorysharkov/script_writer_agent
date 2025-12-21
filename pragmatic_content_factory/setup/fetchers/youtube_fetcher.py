"""YouTube video fetcher using Gemini video understanding."""

import os
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
import structlog

logger = structlog.get_logger(__name__)

# Gemini model for video understanding
DEFAULT_MODEL = "gemini-2.0-flash"


@dataclass
class FetchedYouTube:
    """Result of processing a YouTube video."""

    url: str
    video_id: str
    title: Optional[str]
    transcription: str
    summary: str
    success: bool
    error: Optional[str] = None

    @property
    def text(self) -> str:
        """Combined transcription and summary for further processing."""
        parts = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.summary:
            parts.append(f"Summary:\n{self.summary}")
        if self.transcription:
            parts.append(f"Transcription:\n{self.transcription}")
        return "\n\n".join(parts)


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats.

    Args:
        url: YouTube URL in any format.

    Returns:
        Video ID string or None if not found.
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
        r"youtube\.com/v/([^&\n?#]+)",
        r"youtube\.com/shorts/([^&\n?#]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def _configure_genai() -> None:
    """Configure the Gemini API client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    genai.configure(api_key=api_key)


async def fetch_youtube(
    url: str,
    model_name: str = DEFAULT_MODEL,
    include_transcription: bool = True,
) -> FetchedYouTube:
    """Process a YouTube video using Gemini video understanding.

    Gemini can directly process YouTube URLs without downloading the video.
    It provides transcription and analysis of the video content.

    Args:
        url: YouTube video URL.
        model_name: Gemini model to use.
        include_transcription: Whether to request full transcription.

    Returns:
        FetchedYouTube with transcription and summary.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return FetchedYouTube(
            url=url,
            video_id="",
            title=None,
            transcription="",
            summary="",
            success=False,
            error=f"Could not extract video ID from URL: {url}",
        )

    try:
        _configure_genai()

        model = genai.GenerativeModel(model_name)

        # Build prompt for comprehensive video analysis
        if include_transcription:
            prompt = """Analyze this YouTube video and provide:

1. **Title**: The video title
2. **Summary**: A detailed summary of all topics discussed, key points, and main arguments (2-3 paragraphs)
3. **Transcription**: A complete transcription of the spoken content

Format your response as:
TITLE: [video title]

SUMMARY:
[detailed summary]

TRANSCRIPTION:
[full transcription of spoken content]

Be thorough and capture all technical concepts, tools, methodologies, and opinions expressed in the video."""
        else:
            prompt = """Analyze this YouTube video and provide:

1. **Title**: The video title
2. **Summary**: A detailed summary of all topics discussed, key points, and main arguments (3-4 paragraphs)

Format your response as:
TITLE: [video title]

SUMMARY:
[detailed summary]

Be thorough and capture all technical concepts, tools, methodologies, and opinions expressed in the video."""

        logger.info("Processing YouTube video with Gemini", url=url, video_id=video_id)

        # Gemini can process YouTube URLs directly
        response = model.generate_content([prompt, url])

        if not response.text:
            return FetchedYouTube(
                url=url,
                video_id=video_id,
                title=None,
                transcription="",
                summary="",
                success=False,
                error="Gemini returned empty response",
            )

        # Parse the response
        text = response.text
        title = None
        summary = ""
        transcription = ""

        # Extract title
        title_match = re.search(r"TITLE:\s*(.+?)(?:\n|SUMMARY:)", text, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()

        # Extract summary
        summary_match = re.search(
            r"SUMMARY:\s*(.+?)(?:TRANSCRIPTION:|$)", text, re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip()

        # Extract transcription
        transcription_match = re.search(r"TRANSCRIPTION:\s*(.+?)$", text, re.DOTALL)
        if transcription_match:
            transcription = transcription_match.group(1).strip()

        # If parsing failed, use the whole response as summary
        if not summary and not transcription:
            summary = text

        logger.info(
            "Successfully processed YouTube video",
            url=url,
            video_id=video_id,
            title=title,
            summary_length=len(summary),
            transcription_length=len(transcription),
        )

        return FetchedYouTube(
            url=url,
            video_id=video_id,
            title=title,
            transcription=transcription,
            summary=summary,
            success=True,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Error processing YouTube video",
            url=url,
            video_id=video_id,
            error=error_msg,
        )
        return FetchedYouTube(
            url=url,
            video_id=video_id or "",
            title=None,
            transcription="",
            summary="",
            success=False,
            error=error_msg,
        )


async def fetch_multiple_youtube(
    urls: list[str],
    model_name: str = DEFAULT_MODEL,
) -> list[FetchedYouTube]:
    """Process multiple YouTube videos sequentially.

    Note: We process sequentially to avoid rate limiting issues with Gemini API.

    Args:
        urls: List of YouTube URLs.
        model_name: Gemini model to use.

    Returns:
        List of FetchedYouTube results.
    """
    results = []
    for url in urls:
        result = await fetch_youtube(url, model_name=model_name)
        results.append(result)
    return results
