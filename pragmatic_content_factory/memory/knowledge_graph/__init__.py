"""Knowledge Graph Worldview Layer - Topics and stances using Neo4j."""

__all__ = []

try:
    from pragmatic_content_factory.memory.knowledge_graph.neo4j_client import kg_client
    __all__.append("kg_client")
except ImportError:
    pass
