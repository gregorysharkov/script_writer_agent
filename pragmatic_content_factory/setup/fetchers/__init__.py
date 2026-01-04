"""Content fetchers for different URL types."""

from pragmatic_content_factory.setup.fetchers.web_fetcher import fetch_webpage
from pragmatic_content_factory.setup.fetchers.pdf_fetcher import (
    fetch_pdf,
    extract_text_from_pdf_bytes,
    extract_text_from_pdf_file,
    ExtractedPDFText,
)
from pragmatic_content_factory.setup.fetchers.youtube_fetcher import fetch_youtube

__all__ = [
    "fetch_webpage",
    "fetch_pdf",
    "fetch_youtube",
    "extract_text_from_pdf_bytes",
    "extract_text_from_pdf_file",
    "ExtractedPDFText",
]
