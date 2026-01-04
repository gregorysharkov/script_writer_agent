"""Librarian tools for memory management operations.

These tools provide write access to both memory layers:
- RAG Constitutional Layer (FAISS): taboo terms, style adjustments
- Knowledge Graph Worldview Layer (Neo4j): entities, relationships, stances

The Librarian agent uses these tools to update memory based on
user feedback and content analysis.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

import structlog
from google.adk.tools import ToolContext

from pragmatic_content_factory.memory.rag.indexer import RAGIndexer
from pragmatic_content_factory.memory.rag.models import DocumentChunk, RAGConfig
from pragmatic_content_factory.setup.fetchers.web_fetcher import fetch_webpage
from pragmatic_content_factory.setup.fetchers.youtube_fetcher import fetch_youtube
from pragmatic_content_factory.setup.fetchers.pdf_fetcher import (
    fetch_pdf,
    extract_text_from_pdf_bytes,
)
from pragmatic_content_factory.setup.processors.translator import translate_to_english
from pragmatic_content_factory.setup.processors.entity_extractor import (
    extract_entities_and_relationships,
    ExtractedEntity,
    ExtractedRelationship,
)
from pragmatic_content_factory.setup.loaders.neo4j_loader import Neo4jLoader

logger = structlog.get_logger(__name__)

# Load paths from config
_config = RAGConfig.load()
TABOO_LIST_PATH = _config.paths.taboo_list
STYLE_ADJUSTMENTS_PATH = _config.paths.style_adjustments


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _detect_url_type(url: str) -> Literal["webpage", "youtube", "pdf"]:
    """Detect the type of URL for appropriate fetching."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    if url_lower.endswith(".pdf"):
        return "pdf"
    return "webpage"


async def _add_to_rag_document(
    document_path: str,
    markdown_entry: str,
    chunk_text: str,
    section: Optional[str] = None,
) -> tuple[bool, int, Optional[str]]:
    """Add content to a RAG document (markdown file + FAISS index).

    Args:
        document_path: Path to the markdown document.
        markdown_entry: Formatted entry to add to markdown.
        chunk_text: Text for the RAG chunk (may differ from markdown).
        section: Optional section header to append under.

    Returns:
        Tuple of (success, chunks_added, error_message).
    """
    try:
        indexer = RAGIndexer()

        if not indexer.add_to_dynamic_document(document_path, markdown_entry, section):
            return False, 0, f"Failed to update {document_path}"

        chunk = DocumentChunk(
            text=chunk_text,
            source_file=document_path,
            chunk_index=0,
            document_type="dynamic",
            original_language="en",
            was_translated=False,
        )
        chunks_added = await indexer.add_chunks([chunk], source_file=document_path)
        return True, chunks_added, None

    except Exception as e:
        return False, 0, str(e)


async def process_urls(urls: list[str]) -> dict:
    """Process URLs to extract entities and relationships, then load to Knowledge Graph.

    This tool fetches content from URLs, extracts entities and relationships
    using LLM analysis, and loads them into the Neo4j knowledge graph.

    Use this tool when:
    - User provides URLs to articles, blog posts, or videos
    - User says "add topics from this article"
    - Content brief contains reference URLs

    Args:
        urls: List of URLs to process. Supports web pages, YouTube videos, and PDFs.

    Returns:
        Dictionary containing:
        - processed: Number of URLs successfully processed
        - failed: Number of URLs that failed
        - entities_added: Total entities added to knowledge graph
        - relationships_added: Total relationships added
        - details: List of processing details per URL
    """
    if not urls:
        return {
            "processed": 0,
            "failed": 0,
            "entities_added": 0,
            "relationships_added": 0,
            "details": [],
            "error": "No URLs provided",
        }

    logger.info("Processing URLs for knowledge graph", url_count=len(urls))

    results = {
        "processed": 0,
        "failed": 0,
        "entities_added": 0,
        "relationships_added": 0,
        "details": [],
    }

    for url in urls:
        url_result = {
            "url": url,
            "success": False,
            "entities": 0,
            "relationships": 0,
            "error": None,
        }

        try:
            # 1. Detect URL type and fetch content
            url_type = _detect_url_type(url)
            logger.info("Fetching content", url=url, type=url_type)

            if url_type == "youtube":
                fetch_result = await fetch_youtube(url)
            elif url_type == "pdf":
                fetch_result = await fetch_pdf(url)
            else:
                fetch_result = await fetch_webpage(url)

            if not fetch_result.success or not fetch_result.text:
                url_result["error"] = fetch_result.error or "Failed to fetch content"
                results["failed"] += 1
                results["details"].append(url_result)
                continue

            # 2. Translate if needed
            translation_result = await translate_to_english(fetch_result.text)
            processed_text = translation_result.translated_text

            # 3. Extract entities and relationships
            extraction_result = await extract_entities_and_relationships(
                processed_text, url
            )

            if not extraction_result.entities and not extraction_result.relationships:
                url_result["error"] = "No entities or relationships extracted"
                results["failed"] += 1
                results["details"].append(url_result)
                continue

            # 4. Load to Neo4j
            async with Neo4jLoader() as loader:
                await loader.create_constraints()
                load_result = await loader.load_extraction_result(extraction_result)

            url_result["success"] = True
            url_result["entities"] = load_result["entities_loaded"]
            url_result["relationships"] = load_result["relationships_loaded"]

            results["processed"] += 1
            results["entities_added"] += load_result["entities_loaded"]
            results["relationships_added"] += load_result["relationships_loaded"]

            logger.info(
                "URL processed successfully",
                url=url,
                entities=load_result["entities_loaded"],
                relationships=load_result["relationships_loaded"],
            )

        except Exception as e:
            url_result["error"] = str(e)
            results["failed"] += 1
            logger.error("Failed to process URL", url=url, error=str(e))

        results["details"].append(url_result)

    logger.info(
        "URL processing completed",
        processed=results["processed"],
        failed=results["failed"],
        entities=results["entities_added"],
        relationships=results["relationships_added"],
    )

    return results


_TABOO_SECTIONS = {
    "hype_terms": "Hype Terms (Avoid Completely)",
    "cliches": "Overused Clichés",
    "emotional_language": "Emotional Language (Replace with Concrete)",
    "emoji": "Prohibited (Emotional)",
}


async def add_taboo_term(
    term: str,
    category: Literal[
        "hype_terms", "cliches", "emotional_language", "emoji"
    ] = "hype_terms",
    replacement: Optional[str] = None,
) -> dict:
    """Add a term to the taboo list and update the RAG index.

    Use when user says "never use X" or identifies corporate/hyped phrases.

    Args:
        term: The term or phrase to prohibit.
        category: hype_terms, cliches, emotional_language, or emoji.
        replacement: Optional suggested replacement.

    Returns:
        Dict with success, term, category, chunks_added, error.
    """
    logger.info("Adding taboo term", term=term, category=category)

    # Format entries
    markdown_entry = f'- "{term}" → {replacement}' if replacement else f'- "{term}"'
    chunk_text = f"Taboo term ({category}): {term}"
    if replacement:
        chunk_text += f" - Replace with: {replacement}"

    success, chunks_added, error = await _add_to_rag_document(
        TABOO_LIST_PATH,
        markdown_entry,
        chunk_text,
        section=_TABOO_SECTIONS.get(category, _TABOO_SECTIONS["hype_terms"]),
    )

    if success:
        logger.info(
            "Taboo term added", term=term, category=category, chunks=chunks_added
        )
    else:
        logger.error("Failed to add taboo term", term=term, error=error)

    return {
        "success": success,
        "term": term,
        "category": category,
        "chunks_added": chunks_added,
        "error": error,
    }


async def add_style_adjustment(
    adjustment: str,
    context: Optional[str] = None,
) -> dict:
    """Add a style adjustment to the guidelines and update RAG index.

    Use when user provides tone/style feedback or formatting preferences.

    Args:
        adjustment: The style adjustment to record.
        context: Optional context for when this applies.

    Returns:
        Dict with success, adjustment, chunks_added, error.
    """
    logger.info("Adding style adjustment", adjustment=adjustment)

    # Format entries
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    markdown_entry = f"\n### [{timestamp}]\n- {adjustment}"
    if context:
        markdown_entry += f"\n  *Context: {context}*"

    chunk_text = f"Style adjustment: {adjustment}"
    if context:
        chunk_text += f" Context: {context}"

    success, chunks_added, error = await _add_to_rag_document(
        STYLE_ADJUSTMENTS_PATH,
        markdown_entry,
        chunk_text,
        section="Adjustment History",
    )

    if success:
        logger.info(
            "Style adjustment added", adjustment=adjustment, chunks=chunks_added
        )
    else:
        logger.error(
            "Failed to add style adjustment", adjustment=adjustment, error=error
        )

    return {
        "success": success,
        "adjustment": adjustment,
        "chunks_added": chunks_added,
        "error": error,
    }


async def add_stance(
    entity_name: str,
    stance_type: Literal["HATES", "PREFERS", "SKEPTICAL_OF", "VALUES"],
    reason: str,
    source_quote: Optional[str] = None,
    confidence: float = 0.9,
) -> dict:
    """Add a stance relationship to the Knowledge Graph.

    Use when user expresses opinions ("I hate X") or clarifies preferences.

    Args:
        entity_name: Name of the entity (tool, concept, problem).
        stance_type: HATES, PREFERS, SKEPTICAL_OF, or VALUES.
        reason: Explanation for the stance.
        source_quote: Optional supporting quote.
        confidence: Confidence score (0-1).

    Returns:
        Dict with success, entity_name, stance_type, error.
    """
    logger.info("Adding stance", entity=entity_name, stance=stance_type)

    quote = source_quote or reason
    entity = ExtractedEntity(
        name=entity_name,
        entity_type="Tool",
        description=f"Entity added via stance: {stance_type}",
        source_quote=quote,
        confidence=confidence,
    )
    relationship = ExtractedRelationship(
        source_entity="Grigory",
        relationship_type=stance_type,
        target_entity=entity_name,
        reason=reason,
        source_quote=quote,
        confidence=confidence,
    )

    try:
        async with Neo4jLoader() as loader:
            await loader.create_constraints()
            await loader.create_person_node("Grigory")
            await loader.load_entity(entity, "user_feedback")
            await loader.load_relationship(relationship, "user_feedback")

        logger.info("Stance added", entity=entity_name, stance=stance_type)
        return {
            "success": True,
            "entity_name": entity_name,
            "stance_type": stance_type,
            "error": None,
        }

    except Exception as e:
        logger.error(
            "Failed to add stance", entity=entity_name, stance=stance_type, error=str(e)
        )
        return {
            "success": False,
            "entity_name": entity_name,
            "stance_type": stance_type,
            "error": str(e),
        }


async def process_pdf_artifacts(tool_context: ToolContext) -> dict:
    """Process PDF file attachments to extract entities and relationships into the Knowledge Graph.

    This tool automatically detects PDF files that were attached by the user
    in the conversation and processes them through the entity extraction pipeline.

    Use this tool when:
    - User attaches a PDF file in the chat
    - User mentions they've attached/uploaded a document
    - You detect PDF artifacts in the conversation context

    Args:
        tool_context: ADK ToolContext (automatically injected) providing access to artifacts.

    Returns:
        Dictionary containing:
        - processed: Number of PDFs successfully processed
        - failed: Number of PDFs that failed
        - entities_added: Total entities added to knowledge graph
        - relationships_added: Total relationships added
        - details: List of processing details per PDF
    """
    results = {
        "processed": 0,
        "failed": 0,
        "entities_added": 0,
        "relationships_added": 0,
        "details": [],
    }

    try:
        # List all available artifacts
        artifact_names = tool_context.list_artifacts()

        if not artifact_names:
            logger.info("No artifacts found in context")
            return {
                **results,
                "message": "No file attachments found in the conversation.",
            }

        # Filter for PDF artifacts
        pdf_artifacts = [
            name for name in artifact_names if name.lower().endswith(".pdf")
        ]

        if not pdf_artifacts:
            logger.info("No PDF artifacts found", total_artifacts=len(artifact_names))
            return {
                **results,
                "message": f"No PDF files found among {len(artifact_names)} attachment(s).",
            }

        logger.info("Processing PDF artifacts", pdf_count=len(pdf_artifacts))

        for artifact_name in pdf_artifacts:
            pdf_result = {
                "filename": artifact_name,
                "success": False,
                "entities": 0,
                "relationships": 0,
                "page_count": 0,
                "error": None,
            }

            try:
                # 1. Load the artifact
                artifact_part = tool_context.load_artifact(artifact_name)

                if artifact_part is None:
                    pdf_result["error"] = "Failed to load artifact"
                    results["failed"] += 1
                    results["details"].append(pdf_result)
                    continue

                # 2. Get the PDF bytes from the artifact
                # The artifact Part contains inline_data with the bytes
                if hasattr(artifact_part, "inline_data") and artifact_part.inline_data:
                    pdf_bytes = artifact_part.inline_data.data
                elif hasattr(artifact_part, "data"):
                    pdf_bytes = artifact_part.data
                else:
                    pdf_result["error"] = "Artifact does not contain binary data"
                    results["failed"] += 1
                    results["details"].append(pdf_result)
                    continue

                # 3. Extract text from PDF bytes
                extraction = extract_text_from_pdf_bytes(pdf_bytes)
                pdf_result["page_count"] = extraction.page_count

                if not extraction.success or not extraction.text:
                    pdf_result["error"] = extraction.error or "Failed to extract text"
                    results["failed"] += 1
                    results["details"].append(pdf_result)
                    continue

                logger.info(
                    "PDF text extracted",
                    filename=artifact_name,
                    pages=extraction.page_count,
                    text_length=len(extraction.text),
                )

                # 4. Translate if needed
                translation_result = await translate_to_english(extraction.text)
                processed_text = translation_result.translated_text

                # 5. Extract entities and relationships
                # Use the artifact filename as the source identifier
                source_id = f"attachment:{artifact_name}"
                entity_extraction = await extract_entities_and_relationships(
                    processed_text, source_id
                )

                if (
                    not entity_extraction.entities
                    and not entity_extraction.relationships
                ):
                    pdf_result["error"] = "No entities or relationships extracted"
                    results["failed"] += 1
                    results["details"].append(pdf_result)
                    continue

                # 6. Load to Neo4j
                async with Neo4jLoader() as loader:
                    await loader.create_constraints()
                    load_result = await loader.load_extraction_result(entity_extraction)

                pdf_result["success"] = True
                pdf_result["entities"] = load_result["entities_loaded"]
                pdf_result["relationships"] = load_result["relationships_loaded"]

                results["processed"] += 1
                results["entities_added"] += load_result["entities_loaded"]
                results["relationships_added"] += load_result["relationships_loaded"]

                logger.info(
                    "PDF artifact processed successfully",
                    filename=artifact_name,
                    entities=load_result["entities_loaded"],
                    relationships=load_result["relationships_loaded"],
                )

            except Exception as e:
                pdf_result["error"] = str(e)
                results["failed"] += 1
                logger.error(
                    "Failed to process PDF artifact",
                    filename=artifact_name,
                    error=str(e),
                )

            results["details"].append(pdf_result)

    except Exception as e:
        logger.error("Error accessing artifacts", error=str(e))
        return {
            **results,
            "error": f"Failed to access artifacts: {str(e)}",
        }

    logger.info(
        "PDF artifact processing completed",
        processed=results["processed"],
        failed=results["failed"],
        entities=results["entities_added"],
        relationships=results["relationships_added"],
    )

    return results
