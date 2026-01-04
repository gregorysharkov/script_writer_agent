"""Knowledge Graph Worldview Layer - Topics and stances using Neo4j.

This module provides access to the Knowledge Graph for querying
worldview context, stances, and entity relationships.

Configuration is loaded from conf/neo4j_config.yaml with
environment variable overrides (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).

Usage:
    from pragmatic_content_factory.memory.knowledge_graph import (
        get_kg_client,
        get_stance,
        query_worldview,
    )

    # Get stance on a tool
    stance = await get_stance("LangChain")

    # Get worldview context for a topic
    context = await query_worldview("MLOps")
"""

# Configuration models
from pragmatic_content_factory.memory.knowledge_graph.models import (
    Neo4jConfig,
    get_neo4j_config,
)

# Client and query functions
from pragmatic_content_factory.memory.knowledge_graph.neo4j_client import (
    KnowledgeGraphClient,
    StanceResult,
    EntityContext,
    WorldviewContext,
    get_kg_client,
    get_stance,
    query_worldview,
)

__all__ = [
    # Config
    "Neo4jConfig",
    "get_neo4j_config",
    # Client
    "KnowledgeGraphClient",
    "StanceResult",
    "EntityContext",
    "WorldviewContext",
    "get_kg_client",
    "get_stance",
    "query_worldview",
]
