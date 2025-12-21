"""Parser for worldview.md to extract source links and metadata."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass
class SourceLink:
    """Represents a source link from worldview.md with its metadata."""

    url: str
    title: Optional[str]
    category: str  # ebooks, blog_posts, videos, social, technical
    link_type: Literal["webpage", "pdf", "youtube"]
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Detect link type based on URL patterns."""
        if self.link_type is None:
            self.link_type = detect_link_type(self.url)


def detect_link_type(url: str) -> Literal["webpage", "pdf", "youtube"]:
    """Detect the type of link based on URL patterns.

    Args:
        url: The URL to analyze.

    Returns:
        The detected link type.
    """
    url_lower = url.lower()

    # YouTube detection
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"

    # PDF detection
    if url_lower.endswith(".pdf"):
        return "pdf"

    # Default to webpage
    return "webpage"


def _normalize_category(header: str) -> str:
    """Normalize section header to category name.

    Args:
        header: The markdown header text (e.g., "## EBooks").

    Returns:
        Normalized category name.
    """
    # Remove ## prefix and clean up
    category = header.lstrip("#").strip().lower()

    # Map to standard category names
    category_map = {
        "ebooks": "ebooks",
        "blog posts & articles": "blog_posts",
        "blog posts": "blog_posts",
        "articles": "blog_posts",
        "videos & podcasts": "videos",
        "videos": "videos",
        "podcasts": "videos",
        "social posts": "social",
        "social": "social",
        "technical writing": "technical",
        "technical": "technical",
    }

    return category_map.get(category, category.replace(" ", "_").replace("&", "and"))


def _parse_link_line(line: str, category: str) -> Optional[SourceLink]:
    """Parse a single link line from the markdown.

    Format: - URL | key: value | key: value

    Args:
        line: The line to parse.
        category: The current category context.

    Returns:
        SourceLink if parsing successful, None otherwise.
    """
    # Remove leading dash and whitespace
    line = line.lstrip("-").strip()

    if not line:
        return None

    # Split by | to get URL and metadata parts
    parts = [p.strip() for p in line.split("|")]

    if not parts:
        return None

    # First part is the URL
    url = parts[0].strip()

    # Validate URL
    if not url.startswith(("http://", "https://")):
        return None

    # Parse metadata from remaining parts
    metadata = {}
    title = None

    for part in parts[1:]:
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip().lower()
            value = value.strip().strip('"').strip("'")

            if key == "title":
                title = value
            else:
                metadata[key] = value

    # Detect link type
    link_type = detect_link_type(url)

    return SourceLink(
        url=url,
        title=title,
        category=category,
        link_type=link_type,
        metadata=metadata,
    )


def parse_worldview(file_path: str | Path) -> list[SourceLink]:
    """Parse worldview.md and extract all source links.

    Args:
        file_path: Path to the worldview.md file.

    Returns:
        List of SourceLink objects.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Worldview file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    links: list[SourceLink] = []
    current_category = "uncategorized"

    for line in lines:
        line = line.strip()

        # Check for section headers
        if line.startswith("##"):
            current_category = _normalize_category(line)
            continue

        # Check for link lines (start with -)
        if line.startswith("-"):
            link = _parse_link_line(line, current_category)
            if link:
                links.append(link)

    return links


def get_links_by_type(
    links: list[SourceLink],
) -> dict[Literal["webpage", "pdf", "youtube"], list[SourceLink]]:
    """Group links by their type.

    Args:
        links: List of source links.

    Returns:
        Dictionary mapping link types to lists of links.
    """
    result: dict[Literal["webpage", "pdf", "youtube"], list[SourceLink]] = {
        "webpage": [],
        "pdf": [],
        "youtube": [],
    }

    for link in links:
        result[link.link_type].append(link)

    return result


def get_links_by_category(links: list[SourceLink]) -> dict[str, list[SourceLink]]:
    """Group links by their category.

    Args:
        links: List of source links.

    Returns:
        Dictionary mapping categories to lists of links.
    """
    result: dict[str, list[SourceLink]] = {}

    for link in links:
        if link.category not in result:
            result[link.category] = []
        result[link.category].append(link)

    return result
