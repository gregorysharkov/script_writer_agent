"""RAG Retriever for querying the Constitutional Layer."""

import asyncio
from typing import Optional

import faiss
import structlog

from pragmatic_content_factory.memory.rag.indexer import (
    RAGIndexer,
    generate_query_embedding,
)
from pragmatic_content_factory.memory.rag.models import (
    RAGConfig,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """Retriever for querying the RAG Constitutional Layer.

    Provides async interface for agents to retrieve relevant style rules
    and brand voice guidelines.
    """

    _instance: Optional["RAGRetriever"] = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize the retriever.

        Args:
            config: RAG configuration. Loads from file if not provided.
        """
        self.config = config or RAGConfig.load()
        self._indexer = RAGIndexer(self.config)
        self._initialized = False

    @classmethod
    async def get_instance(cls, config: Optional[RAGConfig] = None) -> "RAGRetriever":
        """Get or create singleton retriever instance.

        Args:
            config: Optional RAG configuration.

        Returns:
            RAGRetriever instance.
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
                await cls._instance.initialize()
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None

    async def initialize(self) -> bool:
        """Initialize the retriever by loading the index.

        Returns:
            True if initialization was successful.
        """
        if self._initialized:
            return True

        # Load index in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, self._indexer.load_index)

        if success:
            self._initialized = True
            logger.info(
                "RAG retriever initialized",
                chunks=len(self._indexer.chunks),
                vectors=self._indexer.index.ntotal if self._indexer.index else 0,
            )
        else:
            logger.warning("RAG retriever initialization failed - index not found")

        return success

    @property
    def is_initialized(self) -> bool:
        """Check if the retriever is initialized."""
        return self._initialized

    @property
    def chunk_count(self) -> int:
        """Get the number of indexed chunks."""
        return len(self._indexer.chunks) if self._initialized else 0

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> RetrievalResult:
        """Retrieve relevant document chunks for a query.

        Args:
            query: The query text to search for.
            top_k: Maximum number of chunks to retrieve.
            min_score: Minimum similarity score threshold (0-1).

        Returns:
            RetrievalResult with matched chunks and scores.
        """
        if not self._initialized:
            logger.warning("Retriever not initialized, returning empty result")
            return RetrievalResult(query=query, chunks=[], scores=[])

        if not query or not query.strip():
            return RetrievalResult(query=query, chunks=[], scores=[])

        # Generate query embedding
        query_embedding = await generate_query_embedding(
            query,
            model=self.config.embedding.model,
        )

        # Normalize for cosine similarity
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        # Search the index
        scores, indices = self._indexer.index.search(query_embedding, top_k)

        # Flatten results
        scores = scores[0]
        indices = indices[0]

        # Filter by minimum score and collect results
        chunks = []
        filtered_scores = []

        for score, idx in zip(scores, indices):
            if idx < 0:  # FAISS returns -1 for not found
                continue
            if score < min_score:
                continue

            chunks.append(self._indexer.chunks[idx])
            filtered_scores.append(float(score))

        logger.info(
            "RAG retrieval completed",
            query_preview=query[:50] + "..." if len(query) > 50 else query,
            results=len(chunks),
            top_score=filtered_scores[0] if filtered_scores else 0,
        )

        return RetrievalResult(
            query=query,
            chunks=chunks,
            scores=filtered_scores,
        )

    async def retrieve_by_type(
        self,
        query: str,
        document_type: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        """Retrieve chunks filtered by document type.

        Args:
            query: The query text.
            document_type: Filter to "static" or "dynamic" documents.
            top_k: Maximum results to return.

        Returns:
            RetrievalResult with filtered chunks.
        """
        # Get more results than needed to allow for filtering
        result = await self.retrieve(query, top_k=top_k * 3)

        # Filter by document type
        filtered_chunks = []
        filtered_scores = []

        for chunk, score in zip(result.chunks, result.scores):
            if chunk.document_type == document_type:
                filtered_chunks.append(chunk)
                filtered_scores.append(score)

                if len(filtered_chunks) >= top_k:
                    break

        return RetrievalResult(
            query=query,
            chunks=filtered_chunks,
            scores=filtered_scores,
        )

    async def get_style_rules(self, context: str, top_k: int = 3) -> str:
        """Convenience method to get style rules as formatted text.

        Args:
            context: Context or topic to find relevant rules for.
            top_k: Number of rule chunks to retrieve.

        Returns:
            Formatted string of relevant style rules.
        """
        result = await self.retrieve(
            f"style rules guidelines voice tone for: {context}",
            top_k=top_k,
        )
        return result.format_context()

    async def get_taboo_terms(self, content: str, top_k: int = 3) -> str:
        """Convenience method to get relevant taboo terms.

        Args:
            content: Content to check against taboo list.
            top_k: Number of taboo chunks to retrieve.

        Returns:
            Formatted string of relevant taboo terms.
        """
        result = await self.retrieve_by_type(
            f"taboo prohibited terms phrases for: {content}",
            document_type="dynamic",
            top_k=top_k,
        )
        return result.format_context()


# Module-level convenience functions
_retriever: Optional[RAGRetriever] = None


async def get_retriever(config: Optional[RAGConfig] = None) -> RAGRetriever:
    """Get the global RAG retriever instance.

    Args:
        config: Optional RAG configuration.

    Returns:
        RAGRetriever instance.
    """
    return await RAGRetriever.get_instance(config)


async def retrieve(query: str, top_k: int = 5) -> RetrievalResult:
    """Retrieve relevant chunks for a query.

    Convenience function that uses the global retriever instance.

    Args:
        query: Query text.
        top_k: Maximum results.

    Returns:
        RetrievalResult.
    """
    retriever = await get_retriever()
    return await retriever.retrieve(query, top_k=top_k)
