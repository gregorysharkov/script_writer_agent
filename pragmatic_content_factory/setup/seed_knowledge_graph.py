"""Main entry point for seeding the knowledge graph from worldview.md."""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import structlog
from pragmatic_content_factory.setup.parsers.worldview_parser import (
    parse_worldview,
    get_links_by_type,
    SourceLink,
)
from pragmatic_content_factory.setup.fetchers.web_fetcher import fetch_webpage
from pragmatic_content_factory.setup.fetchers.pdf_fetcher import fetch_pdf
from pragmatic_content_factory.setup.fetchers.youtube_fetcher import fetch_youtube
from pragmatic_content_factory.setup.processors.translator import translate_to_english
from pragmatic_content_factory.setup.processors.entity_extractor import (
    extract_entities_and_relationships,
    deduplicate_entities,
    ExtractionResult,
)
from pragmatic_content_factory.setup.loaders.neo4j_loader import Neo4jLoader

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Default paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # script_writer_agent/
DEFAULT_WORLDVIEW_PATH = Path(__file__).parent.parent / "data" / "seed" / "worldview.md"
DEFAULT_DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "downloaded"
PROCESSED_FILE = DEFAULT_DOWNLOAD_DIR / ".processed.json"


@dataclass
class FetchedContent:
    """Container for fetched content from any source."""

    url: str
    text: str
    title: Optional[str]
    source_type: str  # webpage, pdf, youtube
    success: bool
    error: Optional[str] = None


def load_processed_urls() -> set[str]:
    """Load the set of already processed URLs."""
    if PROCESSED_FILE.exists():
        try:
            data = json.loads(PROCESSED_FILE.read_text())
            return set(data.get("urls", []))
        except Exception:
            pass
    return set()


def save_processed_urls(urls: set[str]) -> None:
    """Save the set of processed URLs."""
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "urls": list(urls),
        "updated_at": datetime.utcnow().isoformat(),
    }
    PROCESSED_FILE.write_text(json.dumps(data, indent=2))


async def fetch_content(link: SourceLink) -> FetchedContent:
    """Fetch content from a source link based on its type.

    Args:
        link: The source link to fetch.

    Returns:
        FetchedContent with the fetched text.
    """
    logger.info(
        "Fetching content",
        url=link.url,
        type=link.link_type,
        title=link.title,
    )

    try:
        if link.link_type == "webpage":
            result = await fetch_webpage(link.url)
            return FetchedContent(
                url=link.url,
                text=result.text,
                title=result.title or link.title,
                source_type="webpage",
                success=result.success,
                error=result.error,
            )

        elif link.link_type == "pdf":
            result = await fetch_pdf(link.url, download_dir=DEFAULT_DOWNLOAD_DIR)
            return FetchedContent(
                url=link.url,
                text=result.text,
                title=link.title,
                source_type="pdf",
                success=result.success,
                error=result.error,
            )

        elif link.link_type == "youtube":
            result = await fetch_youtube(link.url)
            return FetchedContent(
                url=link.url,
                text=result.text,
                title=result.title or link.title,
                source_type="youtube",
                success=result.success,
                error=result.error,
            )

        else:
            return FetchedContent(
                url=link.url,
                text="",
                title=link.title,
                source_type=link.link_type,
                success=False,
                error=f"Unknown link type: {link.link_type}",
            )

    except Exception as e:
        logger.error("Error fetching content", url=link.url, error=str(e))
        return FetchedContent(
            url=link.url,
            text="",
            title=link.title,
            source_type=link.link_type,
            success=False,
            error=str(e),
        )


async def process_content(content: FetchedContent) -> tuple[str, str]:
    """Process fetched content: translate if needed.

    Args:
        content: The fetched content to process.

    Returns:
        Tuple of (processed_text, source_url).
    """
    if not content.success or not content.text:
        return "", content.url

    # Translate to English if needed
    logger.info("Processing content", url=content.url, text_length=len(content.text))

    translation_result = await translate_to_english(content.text)

    if translation_result.was_translated:
        logger.info(
            "Content translated",
            url=content.url,
            source_language=translation_result.source_language,
        )

    return translation_result.translated_text, content.url


async def seed_knowledge_graph(
    worldview_path: Optional[Path] = None,
    force: bool = False,
    skip_fetch: bool = False,
) -> dict:
    """Main function to seed the knowledge graph.

    Args:
        worldview_path: Path to worldview.md file.
        force: If True, reprocess all URLs even if already processed.
        skip_fetch: If True, skip fetching and use only previously fetched content.

    Returns:
        Dictionary with processing statistics.
    """
    worldview_path = worldview_path or DEFAULT_WORLDVIEW_PATH

    logger.info("Starting knowledge graph seeding", worldview_path=str(worldview_path))

    # 1. Parse worldview.md
    logger.info("Parsing worldview.md...")
    links = parse_worldview(worldview_path)
    links_by_type = get_links_by_type(links)

    logger.info(
        "Links parsed",
        total=len(links),
        webpages=len(links_by_type["webpage"]),
        pdfs=len(links_by_type["pdf"]),
        youtube=len(links_by_type["youtube"]),
    )

    # Load previously processed URLs
    processed_urls = set() if force else load_processed_urls()
    if processed_urls:
        logger.info("Found previously processed URLs", count=len(processed_urls))

    # Filter out already processed
    if not force:
        links = [link for link in links if link.url not in processed_urls]
        logger.info("Links to process after filtering", count=len(links))

    if not links and not force:
        logger.info("No new links to process")
        return {"status": "no_new_links", "processed": 0}

    # 2. Fetch content
    fetched_contents: list[FetchedContent] = []

    if not skip_fetch:
        logger.info("Fetching content from sources...")
        for link in links:
            content = await fetch_content(link)
            fetched_contents.append(content)

        successful_fetches = sum(1 for c in fetched_contents if c.success)
        logger.info(
            "Content fetching completed",
            successful=successful_fetches,
            failed=len(fetched_contents) - successful_fetches,
        )

    # 3. Process and translate content
    logger.info("Processing and translating content...")
    processed_contents: list[tuple[str, str]] = []

    for content in fetched_contents:
        if content.success and content.text:
            processed_text, url = await process_content(content)
            if processed_text:
                processed_contents.append((processed_text, url))

    logger.info("Content processing completed", processed_count=len(processed_contents))

    if not processed_contents:
        logger.warning("No content to extract entities from")
        return {
            "status": "no_content",
            "links_parsed": len(links),
            "fetched": len(fetched_contents),
            "processed": 0,
        }

    # 4. Extract entities and relationships
    logger.info("Extracting entities and relationships...")
    extraction_results: list[ExtractionResult] = []
    successfully_extracted_urls: list[str] = []

    for text, source_url in processed_contents:
        result = await extract_entities_and_relationships(text, source_url)
        extraction_results.append(result)

        # Track URLs that had successful extraction (at least some entities or relationships)
        if result.entities or result.relationships:
            successfully_extracted_urls.append(source_url)

        logger.info(
            "Extracted from source",
            url=source_url,
            entities=len(result.entities),
            relationships=len(result.relationships),
        )

    # 5. Deduplicate entities
    logger.info("Deduplicating entities...")
    entities, relationships = deduplicate_entities(extraction_results)

    logger.info(
        "Deduplication completed",
        unique_entities=len(entities),
        total_relationships=len(relationships),
    )

    # 6. Load to Neo4j
    logger.info("Loading to Neo4j...")

    async with Neo4jLoader() as loader:
        await loader.create_constraints()
        load_result = await loader.load_all(entities, relationships)

        # Get final stats
        stats = await loader.get_stats()

    # Only mark URLs as processed after successful graph update
    for url in successfully_extracted_urls:
        processed_urls.add(url)
    save_processed_urls(processed_urls)
    logger.info("Marked URLs as processed", count=len(successfully_extracted_urls))

    logger.info(
        "Knowledge graph seeding completed",
        entities_loaded=load_result["entities_loaded"],
        relationships_loaded=load_result["relationships_loaded"],
        graph_stats=stats,
    )

    return {
        "status": "success",
        "links_parsed": len(links),
        "content_fetched": len(fetched_contents),
        "content_processed": len(processed_contents),
        "entities_extracted": len(entities),
        "relationships_extracted": len(relationships),
        "entities_loaded": load_result["entities_loaded"],
        "relationships_loaded": load_result["relationships_loaded"],
        "graph_stats": stats,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the knowledge graph from worldview.md"
    )
    parser.add_argument(
        "--worldview",
        "-w",
        type=Path,
        default=DEFAULT_WORLDVIEW_PATH,
        help="Path to worldview.md file",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force reprocessing of all URLs",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetching, use only previously downloaded content",
    )

    args = parser.parse_args()

    # Load environment variables from project root
    load_dotenv(PROJECT_ROOT / ".env")

    # Check for required environment variables
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set")
        sys.exit(1)

    # Run the seeding
    try:
        result = asyncio.run(
            seed_knowledge_graph(
                worldview_path=args.worldview,
                force=args.force,
                skip_fetch=args.skip_fetch,
            )
        )

        print("\n" + "=" * 60)
        print("KNOWLEDGE GRAPH SEEDING RESULTS")
        print("=" * 60)
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
        print("=" * 60)

    except Exception as e:
        logger.exception("Knowledge graph seeding failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
