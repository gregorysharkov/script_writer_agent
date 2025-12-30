# Suppress gRPC ALTS warning (not running on GCP)
import os

os.environ["GRPC_VERBOSITY"] = "ERROR"

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

__all__ = []

# RAG Constitutional Layer
try:
    from pragmatic_content_factory.memory.rag import (
        RAGConfig,
        RAGIndexer,
        RAGRetriever,
        get_retriever,
        retrieve,
    )

    __all__.extend(
        [
            "RAGConfig",
            "RAGIndexer",
            "RAGRetriever",
            "get_retriever",
            "retrieve",
        ]
    )
except ImportError:
    pass

# Knowledge Graph Worldview Layer (not yet implemented)
# try:
#     from pragmatic_content_factory.memory.knowledge_graph import kg_client
#     __all__.append("kg_client")
# except ImportError:
#     pass
