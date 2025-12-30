"""RAG Constitutional Layer - Style and rules retrieval using FAISS.

This module provides the RAG (Retrieval-Augmented Generation) layer for
storing and retrieving brand voice, tone, and style rules. It consists of:

- **Models**: Pydantic models for configuration, chunks, and results
- **Indexer**: FAISS index creation with Gemini embeddings
- **Retriever**: Async query interface for agents

Usage:
    # Get the retriever (loads index on first call)
    from pragmatic_content_factory.memory.rag import get_retriever, retrieve

    retriever = await get_retriever()
    result = await retriever.retrieve("voice tone guidelines")

    # Or use the convenience function
    result = await retrieve("taboo terms to avoid")
"""

__all__ = [
    # Models
    "RAGConfig",
    "DocumentChunk",
    "IndexManifest",
    "RetrievalResult",
    # Indexer
    "RAGIndexer",
    "create_indexer",
    # Retriever
    "RAGRetriever",
    "get_retriever",
    "retrieve",
]

# Models
from pragmatic_content_factory.memory.rag.models import (
    RAGConfig,
    DocumentChunk,
    IndexManifest,
    RetrievalResult,
)

# Indexer
from pragmatic_content_factory.memory.rag.indexer import (
    RAGIndexer,
    create_indexer,
)

# Retriever
from pragmatic_content_factory.memory.rag.retriever import (
    RAGRetriever,
    get_retriever,
    retrieve,
)
