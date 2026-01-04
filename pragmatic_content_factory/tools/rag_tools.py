"""RAG query tools for ADK agents.

These tools provide agents with access to the RAG Constitutional Layer
for querying style rules, voice guidelines, and taboo terms.
"""

import structlog
from pragmatic_content_factory.memory.rag import get_retriever

logger = structlog.get_logger(__name__)


async def query_style_rules(context: str, top_k: int = 5) -> dict:
    """Query the RAG index for relevant style rules and voice guidelines.

    Use this tool to get brand voice guidelines, tone rules, and
    style requirements for content generation. Essential for
    maintaining consistent brand voice.

    Args:
        context: The context or topic to find relevant style rules for.
            Examples: "writing introduction", "technical explanation", "call to action"
        top_k: Maximum number of relevant chunks to retrieve (default: 5).

    Returns:
        Dictionary containing:
        - query: The original query
        - rules: Formatted string of relevant style rules
        - chunks: List of matched chunks with scores
    """
    try:
        retriever = await get_retriever()
        result = await retriever.retrieve(
            f"style rules guidelines voice tone for: {context}",
            top_k=top_k,
        )

        chunks_data = [
            {
                "text": chunk.text,
                "source": chunk.source_file,
                "type": chunk.document_type,
                "score": score,
            }
            for chunk, score in zip(result.chunks, result.scores)
        ]

        logger.info(
            "Style rules query completed",
            context=context,
            chunks_found=len(chunks_data),
        )

        return {
            "query": context,
            "rules": result.format_context(),
            "chunks": chunks_data,
        }

    except Exception as e:
        logger.error("Failed to query style rules", context=context, error=str(e))
        return {
            "query": context,
            "rules": "",
            "chunks": [],
            "error": str(e),
        }


async def query_taboos(content: str, top_k: int = 5) -> dict:
    """Query the RAG index for taboo terms and prohibited phrases.

    Use this tool to check content against the taboo list and
    identify phrases that should be avoided. Essential for
    the Ruthless Critic's quality gate function.

    Args:
        content: The content to check against taboo terms.
            Can be a draft section or specific phrases to verify.
        top_k: Maximum number of relevant chunks to retrieve (default: 5).

    Returns:
        Dictionary containing:
        - query: The original query
        - taboos: Formatted string of relevant taboo terms
        - chunks: List of matched chunks with scores
    """
    try:
        retriever = await get_retriever()
        result = await retriever.retrieve_by_type(
            f"taboo prohibited terms phrases hype buzzwords for: {content}",
            document_type="dynamic",
            top_k=top_k,
        )

        chunks_data = [
            {
                "text": chunk.text,
                "source": chunk.source_file,
                "score": score,
            }
            for chunk, score in zip(result.chunks, result.scores)
        ]

        logger.info(
            "Taboo query completed",
            content_preview=content[:50] + "..." if len(content) > 50 else content,
            chunks_found=len(chunks_data),
        )

        return {
            "query": content,
            "taboos": result.format_context(),
            "chunks": chunks_data,
        }

    except Exception as e:
        logger.error("Failed to query taboos", error=str(e))
        return {
            "query": content,
            "taboos": "",
            "chunks": [],
            "error": str(e),
        }


async def query_brand_voice(topic: str, top_k: int = 5) -> dict:
    """Query the RAG index for brand voice and persona guidelines.

    Use this tool to understand the brand persona, tone of voice,
    and communication style for a specific topic or context.

    Args:
        topic: The topic or context to find brand voice guidelines for.
        top_k: Maximum number of relevant chunks to retrieve (default: 5).

    Returns:
        Dictionary containing:
        - query: The original query
        - guidelines: Formatted string of brand voice guidelines
        - chunks: List of matched chunks with scores
    """
    try:
        retriever = await get_retriever()
        result = await retriever.retrieve(
            f"brand voice persona tone communication style for: {topic}",
            top_k=top_k,
        )

        chunks_data = [
            {
                "text": chunk.text,
                "source": chunk.source_file,
                "type": chunk.document_type,
                "score": score,
            }
            for chunk, score in zip(result.chunks, result.scores)
        ]

        logger.info(
            "Brand voice query completed",
            topic=topic,
            chunks_found=len(chunks_data),
        )

        return {
            "query": topic,
            "guidelines": result.format_context(),
            "chunks": chunks_data,
        }

    except Exception as e:
        logger.error("Failed to query brand voice", topic=topic, error=str(e))
        return {
            "query": topic,
            "guidelines": "",
            "chunks": [],
            "error": str(e),
        }
