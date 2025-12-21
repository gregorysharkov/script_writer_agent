"""Translation processor using Gemini for language detection and translation."""

import os
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
import structlog

logger = structlog.get_logger(__name__)

# Gemini model for translation
DEFAULT_MODEL = "gemini-2.0-flash"

# Maximum characters to send in one request (to avoid token limits)
MAX_CHUNK_SIZE = 30000


@dataclass
class TranslationResult:
    """Result of translation process."""

    original_text: str
    translated_text: str
    source_language: str
    was_translated: bool
    success: bool
    error: Optional[str] = None


def _configure_genai() -> None:
    """Configure the Gemini API client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    genai.configure(api_key=api_key)


async def detect_language(text: str, model_name: str = DEFAULT_MODEL) -> str:
    """Detect the language of the given text.

    Args:
        text: Text to analyze.
        model_name: Gemini model to use.

    Returns:
        ISO 639-1 language code (e.g., "en", "ru", "de").
    """
    _configure_genai()
    model = genai.GenerativeModel(model_name)

    # Use a sample if text is very long
    sample = text[:5000] if len(text) > 5000 else text

    prompt = f"""Detect the primary language of the following text. 
Respond with ONLY the ISO 639-1 two-letter language code (e.g., "en" for English, "ru" for Russian, "de" for German).
Do not include any other text in your response.

Text:
{sample}"""

    response = model.generate_content(prompt)
    language = response.text.strip().lower()

    # Validate it's a 2-letter code
    if len(language) == 2 and language.isalpha():
        return language

    # Try to extract from response if it contains more text
    for word in response.text.split():
        word = word.strip().lower()
        if len(word) == 2 and word.isalpha():
            return word

    logger.warning(
        "Could not parse language code from response",
        response=response.text,
    )
    return "unknown"


async def translate_chunk(
    text: str,
    source_language: str,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """Translate a single chunk of text to English.

    Args:
        text: Text to translate.
        source_language: Source language code.
        model_name: Gemini model to use.

    Returns:
        Translated text in English.
    """
    _configure_genai()
    model = genai.GenerativeModel(model_name)

    prompt = f"""Translate the following text from {source_language} to English.
Preserve all technical terms, code snippets, URLs, and proper nouns.
Maintain the original formatting and structure.
Only output the translation, no explanations.

Text to translate:
{text}"""

    response = model.generate_content(prompt)
    return response.text


async def translate_to_english(
    text: str,
    source_language: str = "auto",
    model_name: str = DEFAULT_MODEL,
) -> TranslationResult:
    """Translate text to English using Gemini.

    Args:
        text: Text to translate.
        source_language: Source language code or "auto" for detection.
        model_name: Gemini model to use.

    Returns:
        TranslationResult with translated text.
    """
    if not text or not text.strip():
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language="unknown",
            was_translated=False,
            success=True,
        )

    try:
        # Detect language if needed
        if source_language == "auto":
            logger.info("Detecting language...")
            source_language = await detect_language(text, model_name)
            logger.info("Detected language", language=source_language)

        # Skip if already English
        if source_language == "en":
            logger.info("Text is already in English, skipping translation")
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="en",
                was_translated=False,
                success=True,
            )

        logger.info(
            "Translating text to English",
            source_language=source_language,
            text_length=len(text),
        )

        # Split into chunks if needed
        if len(text) <= MAX_CHUNK_SIZE:
            translated = await translate_chunk(text, source_language, model_name)
        else:
            # Split by paragraphs to maintain context
            paragraphs = text.split("\n\n")
            chunks = []
            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) + 2 <= MAX_CHUNK_SIZE:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = para + "\n\n"

            if current_chunk:
                chunks.append(current_chunk)

            # Translate each chunk
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                logger.info(
                    "Translating chunk",
                    chunk_number=i + 1,
                    total_chunks=len(chunks),
                )
                translated_chunk = await translate_chunk(chunk, source_language, model_name)
                translated_chunks.append(translated_chunk)

            translated = "\n\n".join(translated_chunks)

        logger.info(
            "Translation completed",
            original_length=len(text),
            translated_length=len(translated),
        )

        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_language=source_language,
            was_translated=True,
            success=True,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error("Translation failed", error=error_msg)
        return TranslationResult(
            original_text=text,
            translated_text=text,  # Return original on failure
            source_language=source_language if source_language != "auto" else "unknown",
            was_translated=False,
            success=False,
            error=error_msg,
        )


async def translate_multiple(
    texts: list[str],
    model_name: str = DEFAULT_MODEL,
) -> list[TranslationResult]:
    """Translate multiple texts to English.

    Note: Processed sequentially to avoid rate limiting.

    Args:
        texts: List of texts to translate.
        model_name: Gemini model to use.

    Returns:
        List of TranslationResult objects.
    """
    results = []
    for text in texts:
        result = await translate_to_english(text, model_name=model_name)
        results.append(result)
    return results
