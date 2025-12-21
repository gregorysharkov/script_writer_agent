"""PDF fetcher - downloads PDFs and extracts text content."""

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import httpx
from pypdf import PdfReader
import structlog

logger = structlog.get_logger(__name__)

# Default download directory
DEFAULT_DOWNLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "downloaded"

# User agent for downloads
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class FetchedPDF:
    """Result of fetching and processing a PDF."""

    url: str
    file_path: Optional[Path]
    text: str
    page_count: int
    success: bool
    error: Optional[str] = None


def _sanitize_filename(url: str) -> str:
    """Create a safe filename from a URL.

    Args:
        url: The source URL.

    Returns:
        A safe filename string.
    """
    parsed = urlparse(url)
    path = unquote(parsed.path)

    # Try to get filename from path
    filename = Path(path).name if path else ""

    # If no filename or not a PDF, create one from URL hash
    if not filename or not filename.lower().endswith(".pdf"):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"document_{url_hash}.pdf"

    # Sanitize: remove special characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    return filename


def _extract_text_from_pdf(file_path: Path) -> tuple[str, int]:
    """Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Tuple of (extracted_text, page_count).
    """
    try:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)

        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

        text = "\n\n".join(text_parts)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text, page_count

    except Exception as e:
        logger.error(
            "Error extracting text from PDF", path=str(file_path), error=str(e)
        )
        raise


async def fetch_pdf(
    url: str,
    download_dir: Optional[Path] = None,
    timeout: float = 120.0,
    max_retries: int = 3,
    force_download: bool = False,
) -> FetchedPDF:
    """Download a PDF and extract its text content.

    Args:
        url: The URL of the PDF to download.
        download_dir: Directory to save PDFs (defaults to data/downloaded).
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        force_download: If True, re-download even if file exists.

    Returns:
        FetchedPDF with the extracted text.
    """
    download_dir = download_dir or DEFAULT_DOWNLOAD_DIR
    download_dir.mkdir(parents=True, exist_ok=True)

    filename = _sanitize_filename(url)
    file_path = download_dir / filename

    # Check if already downloaded
    if file_path.exists() and not force_download:
        logger.info("PDF already downloaded, extracting text", path=str(file_path))
        try:
            text, page_count = _extract_text_from_pdf(file_path)
            return FetchedPDF(
                url=url,
                file_path=file_path,
                text=text,
                page_count=page_count,
                success=True,
            )
        except Exception as e:
            logger.warning(
                "Failed to extract from existing PDF, will re-download",
                path=str(file_path),
                error=str(e),
            )

    # Download the PDF
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,*/*",
    }

    last_error = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                logger.info("Downloading PDF", url=url, attempt=attempt + 1)
                response = await client.get(url)
                response.raise_for_status()

                # Verify content type
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not url.lower().endswith(
                    ".pdf"
                ):
                    logger.warning(
                        "Response may not be PDF",
                        url=url,
                        content_type=content_type,
                    )

                # Save to file
                file_path.write_bytes(response.content)
                logger.info(
                    "PDF downloaded successfully",
                    url=url,
                    path=str(file_path),
                    size_bytes=len(response.content),
                )

                # Extract text
                text, page_count = _extract_text_from_pdf(file_path)

                if not text.strip():
                    return FetchedPDF(
                        url=url,
                        file_path=file_path,
                        text="",
                        page_count=page_count,
                        success=False,
                        error="PDF contains no extractable text (may be image-based)",
                    )

                return FetchedPDF(
                    url=url,
                    file_path=file_path,
                    text=text,
                    page_count=page_count,
                    success=True,
                )

        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
            logger.warning("HTTP error downloading PDF", url=url, error=last_error)

        except httpx.TimeoutException:
            last_error = "Request timed out"
            logger.warning("Timeout downloading PDF", url=url)

        except httpx.RequestError as e:
            last_error = f"Request error: {str(e)}"
            logger.warning("Request error downloading PDF", url=url, error=str(e))

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error downloading PDF", url=url, error=str(e))

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    return FetchedPDF(
        url=url,
        file_path=None,
        text="",
        page_count=0,
        success=False,
        error=last_error or "Unknown error",
    )


async def fetch_multiple_pdfs(
    urls: list[str],
    download_dir: Optional[Path] = None,
    max_concurrent: int = 2,
) -> list[FetchedPDF]:
    """Download multiple PDFs with concurrency limit.

    Args:
        urls: List of PDF URLs to download.
        download_dir: Directory to save PDFs.
        max_concurrent: Maximum number of concurrent downloads.

    Returns:
        List of FetchedPDF results.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(url: str) -> FetchedPDF:
        async with semaphore:
            return await fetch_pdf(url, download_dir=download_dir)

    tasks = [fetch_with_semaphore(url) for url in urls]
    return await asyncio.gather(*tasks)
