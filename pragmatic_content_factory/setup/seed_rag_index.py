"""Main entry point for seeding the RAG Constitutional Layer index."""

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import structlog
from tqdm import tqdm

from pragmatic_content_factory.memory.rag.indexer import (
    RAGIndexer,
    _chunk_text,
    _compute_file_hash,
)
from pragmatic_content_factory.memory.rag.models import (
    DocumentChunk,
    DocumentInfo,
    RAGConfig,
)
from pragmatic_content_factory.setup.fetchers.pdf_fetcher import _extract_text_from_pdf
from pragmatic_content_factory.setup.processors.translator import translate_to_english

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
PCF_ROOT = Path(__file__).parent.parent  # pragmatic_content_factory/
STATIC_DIR = PCF_ROOT / "data" / "static"
DYNAMIC_DIR = PCF_ROOT / "data" / "dynamic"


@dataclass
class ProcessedDocument:
    """Container for a processed document."""

    file_path: Path
    original_text: str
    translated_text: str
    original_language: str
    was_translated: bool
    document_type: str  # "static" or "dynamic"


def get_document_paths() -> tuple[list[Path], list[Path]]:
    """Get paths to all documents that should be indexed.

    Returns:
        Tuple of (static_docs, dynamic_docs).
    """
    static_docs = []
    dynamic_docs = []

    # Static PDFs
    if STATIC_DIR.exists():
        static_docs = list(STATIC_DIR.glob("*.pdf"))

    # Dynamic markdown files
    if DYNAMIC_DIR.exists():
        dynamic_docs = list(DYNAMIC_DIR.glob("*.md"))

    return static_docs, dynamic_docs


def read_markdown_file(file_path: Path) -> str:
    """Read a markdown file.

    Args:
        file_path: Path to the markdown file.

    Returns:
        File contents as string.
    """
    with open(file_path, encoding="utf-8") as f:
        return f.read()


async def process_document(
    file_path: Path,
    document_type: str,
) -> Optional[ProcessedDocument]:
    """Process a single document: extract text and translate.

    Args:
        file_path: Path to the document.
        document_type: "static" or "dynamic".

    Returns:
        ProcessedDocument or None if processing failed.
    """
    logger.info("Processing document", path=str(file_path), type=document_type)

    try:
        # Extract text based on file type
        if file_path.suffix.lower() == ".pdf":
            text, page_count = _extract_text_from_pdf(file_path)
            logger.info("Extracted PDF text", pages=page_count, chars=len(text))
        elif file_path.suffix.lower() == ".md":
            text = read_markdown_file(file_path)
            logger.info("Read markdown file", chars=len(text))
        else:
            logger.warning("Unsupported file type", path=str(file_path))
            return None

        if not text or not text.strip():
            logger.warning("Empty document", path=str(file_path))
            return None

        # Translate to English if needed
        translation_result = await translate_to_english(text)

        return ProcessedDocument(
            file_path=file_path,
            original_text=text,
            translated_text=translation_result.translated_text,
            original_language=translation_result.source_language,
            was_translated=translation_result.was_translated,
            document_type=document_type,
        )

    except Exception as e:
        logger.error("Failed to process document", path=str(file_path), error=str(e))
        return None


def create_chunks(
    processed_doc: ProcessedDocument,
    config: RAGConfig,
) -> list[DocumentChunk]:
    """Create chunks from a processed document.

    Args:
        processed_doc: The processed document.
        config: RAG configuration.

    Returns:
        List of DocumentChunk objects.
    """
    # Use translated text for chunking
    text = processed_doc.translated_text

    # Chunk the text
    chunk_texts = _chunk_text(
        text,
        chunk_size=config.chunking.chunk_size,
        chunk_overlap=config.chunking.chunk_overlap,
    )

    # Create DocumentChunk objects
    rel_path = str(processed_doc.file_path.relative_to(PCF_ROOT))

    chunks = []
    for i, chunk_text in enumerate(chunk_texts):
        chunk = DocumentChunk(
            text=chunk_text,
            source_file=rel_path,
            chunk_index=i,
            document_type=processed_doc.document_type,
            original_language=processed_doc.original_language,
            was_translated=processed_doc.was_translated,
        )
        chunks.append(chunk)

    return chunks


async def seed_rag_index(
    force: bool = False,
    check_only: bool = False,
) -> dict:
    """Main function to seed the RAG index.

    Args:
        force: If True, rebuild index regardless of changes.
        check_only: If True, only check what would be rebuilt.

    Returns:
        Dictionary with processing statistics.
    """
    logger.info("Starting RAG index seeding", force=force, check_only=check_only)

    # Load configuration
    config = RAGConfig.load()
    # pylint: disable=no-member  # pylint doesn't understand Pydantic models
    logger.info(
        "Loaded RAG configuration",
        chunk_size=config.chunking.chunk_size,
        chunk_overlap=config.chunking.chunk_overlap,
        embedding_model=config.embedding.model,
    )
    # pylint: enable=no-member

    # Get document paths
    static_docs, dynamic_docs = get_document_paths()
    all_docs = static_docs + dynamic_docs

    logger.info(
        "Found documents",
        static=len(static_docs),
        dynamic=len(dynamic_docs),
        total=len(all_docs),
    )

    if not all_docs:
        logger.warning("No documents found to index")
        return {"status": "no_documents", "processed": 0}

    # Create indexer and check if rebuild is needed
    indexer = RAGIndexer(config)

    if not force:
        needs_rebuild, reasons = indexer.check_needs_rebuild(all_docs)

        if not needs_rebuild:
            logger.info("Index is up to date, no rebuild needed")
            return {
                "status": "up_to_date",
                "message": "Index is up to date",
            }

        logger.info("Index needs rebuild", reasons=reasons)

        if check_only:
            return {
                "status": "needs_rebuild",
                "reasons": reasons,
            }
    else:
        if check_only:
            return {
                "status": "would_force_rebuild",
                "message": "Force flag would trigger full rebuild",
            }

    # Process all documents
    logger.info("Processing documents...")
    all_chunks: list[DocumentChunk] = []
    document_infos: dict[str, DocumentInfo] = {}

    # Process static documents with progress bar
    if static_docs:
        for doc_path in tqdm(static_docs, desc="Processing static docs", unit="doc"):
            processed = await process_document(doc_path, "static")
            if processed:
                chunks = create_chunks(processed, config)
                all_chunks.extend(chunks)

                rel_path = str(doc_path.relative_to(PCF_ROOT))
                document_infos[rel_path] = DocumentInfo(
                    file_hash=_compute_file_hash(doc_path),
                    chunk_count=len(chunks),
                    original_language=processed.original_language,
                )

    # Process dynamic documents with progress bar
    if dynamic_docs:
        for doc_path in tqdm(dynamic_docs, desc="Processing dynamic docs", unit="doc"):
            processed = await process_document(doc_path, "dynamic")
            if processed:
                chunks = create_chunks(processed, config)
                all_chunks.extend(chunks)

                rel_path = str(doc_path.relative_to(PCF_ROOT))
                document_infos[rel_path] = DocumentInfo(
                    file_hash=_compute_file_hash(doc_path),
                    chunk_count=len(chunks),
                    original_language=processed.original_language,
                )

    if not all_chunks:
        logger.warning("No chunks created from documents")
        return {
            "status": "no_chunks",
            "documents_found": len(all_docs),
            "chunks_created": 0,
        }

    # Build the index
    logger.info("Building FAISS index...", total_chunks=len(all_chunks))
    await indexer.build_index(all_chunks, document_infos)

    result = {
        "status": "success",
        "documents_processed": len(document_infos),
        "chunks_created": len(all_chunks),
        "static_docs": len(static_docs),
        "dynamic_docs": len(dynamic_docs),
    }

    logger.info("RAG index seeding completed", **result)
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the RAG Constitutional Layer index"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force rebuild of index regardless of changes",
    )
    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        help="Check what would be rebuilt without actually rebuilding",
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
            seed_rag_index(
                force=args.force,
                check_only=args.check,
            )
        )

        print("\n" + "=" * 60)
        print("RAG INDEX SEEDING RESULTS")
        print("=" * 60)
        for key, value in result.items():
            if isinstance(value, list):
                print(f"\n{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
        print("=" * 60)

        # Exit with appropriate code
        if result.get("status") in ["success", "up_to_date"]:
            sys.exit(0)
        elif result.get("status") == "needs_rebuild":
            sys.exit(0)  # Check mode, not an error
        else:
            sys.exit(1)

    except Exception as e:
        logger.exception("RAG index seeding failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
