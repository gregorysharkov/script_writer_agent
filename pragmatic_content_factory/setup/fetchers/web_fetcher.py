"""Web page content fetcher using httpx and BeautifulSoup."""

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger(__name__)

# Common user agent to avoid being blocked
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Tags to remove (typically non-content elements)
REMOVE_TAGS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "aside",
    "noscript",
    "iframe",
    "form",
    "button",
]

# Tags that typically contain main content
CONTENT_TAGS = ["article", "main", "div.content", "div.post", "div.article"]


@dataclass
class FetchedContent:
    """Result of fetching web content."""

    url: str
    title: Optional[str]
    text: str
    success: bool
    error: Optional[str] = None


def _extract_text_from_html(html: str, url: str) -> tuple[Optional[str], str]:
    """Extract clean text content from HTML.

    Args:
        html: Raw HTML content.
        url: Source URL for logging.

    Returns:
        Tuple of (title, text_content).
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title = None
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Also try og:title or h1
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content")

    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # Remove non-content tags
    for tag in REMOVE_TAGS:
        for element in soup.find_all(tag):
            element.decompose()

    # Try to find main content area
    main_content = None

    # Try common content containers
    for selector in ["article", "main", "[role='main']", ".content", ".post-content"]:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # If no specific content area found, use body
    if not main_content:
        main_content = soup.find("body")

    if not main_content:
        main_content = soup

    # Extract text
    text = main_content.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    return title, text


async def fetch_webpage(
    url: str,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> FetchedContent:
    """Fetch and extract text content from a web page.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.

    Returns:
        FetchedContent with the extracted text.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    last_error = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                logger.info("Fetching webpage", url=url, attempt=attempt + 1)
                response = await client.get(url)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    logger.warning(
                        "Unexpected content type",
                        url=url,
                        content_type=content_type,
                    )

                html = response.text
                title, text = _extract_text_from_html(html, url)

                if not text:
                    return FetchedContent(
                        url=url,
                        title=title,
                        text="",
                        success=False,
                        error="No text content extracted from page",
                    )

                logger.info(
                    "Successfully fetched webpage",
                    url=url,
                    title=title,
                    text_length=len(text),
                )

                return FetchedContent(
                    url=url,
                    title=title,
                    text=text,
                    success=True,
                )

        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
            logger.warning("HTTP error fetching page", url=url, error=last_error)

        except httpx.TimeoutException:
            last_error = "Request timed out"
            logger.warning("Timeout fetching page", url=url)

        except httpx.RequestError as e:
            last_error = f"Request error: {str(e)}"
            logger.warning("Request error fetching page", url=url, error=str(e))

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error("Unexpected error fetching page", url=url, error=str(e))

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    return FetchedContent(
        url=url,
        title=None,
        text="",
        success=False,
        error=last_error or "Unknown error",
    )


async def fetch_multiple_webpages(
    urls: list[str],
    max_concurrent: int = 3,
) -> list[FetchedContent]:
    """Fetch multiple web pages with concurrency limit.

    Args:
        urls: List of URLs to fetch.
        max_concurrent: Maximum number of concurrent requests.

    Returns:
        List of FetchedContent results.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(url: str) -> FetchedContent:
        async with semaphore:
            return await fetch_webpage(url)

    tasks = [fetch_with_semaphore(url) for url in urls]
    return await asyncio.gather(*tasks)
