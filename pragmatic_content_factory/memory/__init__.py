"""The Brain - Memory layer components for RAG and Knowledge Graph.

This module provides access to the two memory layers:

1. **RAG Constitutional Layer** (`memory.rag`)
   - Stores brand voice, tone, and style rules
   - Uses FAISS + Gemini embeddings
   - Queried by Voice Architect and Ruthless Critic

2. **Knowledge Graph Worldview Layer** (`memory.knowledge_graph`)
   - Stores relationships between concepts and stances
   - Uses Neo4j
   - Queried by Deep Analyst

Usage:
    from pragmatic_content_factory.memory.rag import get_retriever, retrieve

    # Get style rules
    result = await retrieve("voice tone guidelines", top_k=5)
"""

# Suppress gRPC ALTS warning (not running on GCP)
import os

# RAG Constitutional Layer
from pragmatic_content_factory.memory.rag import (
    RAGConfig,
    RAGIndexer,
    RAGRetriever,
    get_retriever,
    retrieve,
)

# Knowledge Graph Worldview Layer
from pragmatic_content_factory.memory.knowledge_graph import (
    KnowledgeGraphClient,
    get_kg_client,
    get_stance,
    query_worldview,
)

__all__ = [
    # RAG
    "RAGConfig",
    "RAGIndexer",
    "RAGRetriever",
    "get_retriever",
    "retrieve",
    # Knowledge Graph
    "KnowledgeGraphClient",
    "get_kg_client",
    "get_stance",
    "query_worldview",
]

# Suppress gRPC ALTS warning (not running on GCP)
os.environ["GRPC_VERBOSITY"] = "ERROR"
