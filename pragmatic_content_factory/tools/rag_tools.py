"""RAG query tools for ADK agents.

These tools provide agents with access to the RAG Constitutional Layer
for querying style rules, voice guidelines, and taboo terms.
"""

from typing import Literal, Optional

import structlog

from pragmatic_content_factory.memory.rag import get_retriever
from pragmatic_content_factory.memory.rag.models import RetrievalResult

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _format_chunks(result: RetrievalResult, include_type: bool = True) -> list[dict]:
    """Format retrieval result chunks for tool response."""
    chunks = []
    for chunk, score in zip(result.chunks, result.scores):
        data = {"text": chunk.text, "source": chunk.source_file, "score": score}
        if include_type:
            data["type"] = chunk.document_type
        chunks.append(data)
    return chunks


async def _query_rag(
    query: str,
    topic: str,
    result_key: str,
    top_k: int,
    log_name: str,
    document_type: Optional[Literal["static", "dynamic"]] = None,
    include_chunk_type: bool = True,
) -> dict:
    """Common RAG query pattern.

    Args:
        query: The full query string to send to retriever.
        topic: Original topic/context for the response dict.
        result_key: Key name for the formatted context in response.
        top_k: Number of chunks to retrieve.
        log_name: Name for logging (e.g., "Style rules").
        document_type: Optional filter by document type.
        include_chunk_type: Whether to include document_type in chunk data.

    Returns:
        Dict with query, result_key, chunks, and optionally error.
    """
    try:
        retriever = await get_retriever()

        if document_type:
            result = await retriever.retrieve_by_type(query, document_type, top_k=top_k)
        else:
            result = await retriever.retrieve(query, top_k=top_k)

        chunks_data = _format_chunks(result, include_type=include_chunk_type)

        logger.info(
            f"{log_name} query completed", topic=topic, chunks_found=len(chunks_data)
        )

        return {
            "query": topic,
            result_key: result.format_context(),
            "chunks": chunks_data,
        }

    except Exception as e:
        logger.error(f"Failed to query {log_name.lower()}", topic=topic, error=str(e))
        return {"query": topic, result_key: "", "chunks": [], "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Public tools
# ─────────────────────────────────────────────────────────────────────────────


async def query_style_rules(context: str, top_k: int = 5) -> dict:
    """Query the RAG index for relevant style rules and voice guidelines.

    Use to get brand voice guidelines, tone rules, and style requirements.

    Args:
        context: The context or topic to find relevant style rules for.
        top_k: Maximum number of relevant chunks to retrieve.

    Returns:
        Dict with query, rules, chunks, and optionally error.
    """
    return await _query_rag(
        query=f"style rules guidelines voice tone for: {context}",
        topic=context,
        result_key="rules",
        top_k=top_k,
        log_name="Style rules",
    )


async def query_taboos(content: str, top_k: int = 5) -> dict:
    """Query the RAG index for taboo terms and prohibited phrases.

    Use to check content against the taboo list. Essential for quality gate.

    Args:
        content: The content to check against taboo terms.
        top_k: Maximum number of relevant chunks to retrieve.

    Returns:
        Dict with query, taboos, chunks, and optionally error.
    """
    return await _query_rag(
        query=f"taboo prohibited terms phrases hype buzzwords for: {content}",
        topic=content,
        result_key="taboos",
        top_k=top_k,
        log_name="Taboo",
        document_type="dynamic",
        include_chunk_type=False,
    )


async def query_brand_voice(topic: str, top_k: int = 5) -> dict:
    """Query the RAG index for brand voice and persona guidelines.

    Use to understand the brand persona, tone, and communication style.

    Args:
        topic: The topic or context to find brand voice guidelines for.
        top_k: Maximum number of relevant chunks to retrieve.

    Returns:
        Dict with query, guidelines, chunks, and optionally error.
    """
    return await _query_rag(
        query=f"brand voice persona tone communication style for: {topic}",
        topic=topic,
        result_key="guidelines",
        top_k=top_k,
        log_name="Brand voice",
    )
