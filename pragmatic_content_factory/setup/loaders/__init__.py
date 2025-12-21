"""Data loaders for persisting extracted knowledge."""

from pragmatic_content_factory.setup.loaders.neo4j_loader import (
    load_to_neo4j,
    Neo4jLoader,
)

__all__ = ["load_to_neo4j", "Neo4jLoader"]
