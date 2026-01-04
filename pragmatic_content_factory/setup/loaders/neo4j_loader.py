"""Neo4j loader for persisting extracted entities and relationships."""

from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog

from pragmatic_content_factory.memory.knowledge_graph.models import (
    Neo4jConfig,
    get_neo4j_config,
)
from pragmatic_content_factory.setup.processors.entity_extractor import (
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
)

logger = structlog.get_logger(__name__)


class Neo4jLoader:
    """Loader for persisting entities and relationships to Neo4j.

    Configuration is loaded from conf/neo4j_config.yaml with
    environment variable overrides (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).
    """

    def __init__(
        self,
        config: Optional[Neo4jConfig] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize the Neo4j loader.

        Args:
            config: Neo4jConfig instance. If not provided, loads from config file.
            uri: Neo4j connection URI (overrides config).
            user: Neo4j username (overrides config).
            password: Neo4j password (overrides config).
        """
        self.config = config or get_neo4j_config()

        # Allow explicit overrides, otherwise use config
        self.uri = uri or self.config.connection.uri
        self.user = user or self.config.connection.user
        self.password = password or self.config.get_password_or_default()

        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        if self._driver is None:
            logger.info("Connecting to Neo4j", uri=self.uri)
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully")

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def __aenter__(self) -> "Neo4jLoader":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def create_constraints(self) -> None:
        """Create uniqueness constraints for entity nodes."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Problem) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (per:Person) REQUIRE per.name IS UNIQUE",
        ]

        async with self._driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    # Constraint may already exist
                    logger.debug(
                        "Constraint creation", constraint=constraint, note=str(e)
                    )

        logger.info("Neo4j constraints created/verified")

    async def create_person_node(self, name: str = "Grigory") -> None:
        """Create the Person node for the brand persona.

        Args:
            name: Name of the person node.
        """
        query = """
        MERGE (p:Person {name: $name})
        SET p.updated_at = datetime()
        RETURN p
        """

        async with self._driver.session() as session:
            await session.run(query, name=name)
            logger.info("Person node created/updated", name=name)

    async def load_entity(
        self,
        entity: ExtractedEntity,
        source_url: str,
    ) -> None:
        """Load a single entity into Neo4j.

        Args:
            entity: The entity to load.
            source_url: URL of the source document.
        """
        # Map entity types to Neo4j labels
        label = entity.entity_type  # Tool, Concept, or Problem

        query = f"""
        MERGE (n:{label} {{name: $name}})
        SET n.description = $description,
            n.source_url = $source_url,
            n.source_quote = $source_quote,
            n.confidence = $confidence,
            n.updated_at = datetime()
        RETURN n
        """

        async with self._driver.session() as session:
            await session.run(
                query,
                name=entity.name,
                description=entity.description,
                source_url=source_url,
                source_quote=entity.source_quote,
                confidence=entity.confidence,
            )

    async def load_relationship(
        self,
        relationship: ExtractedRelationship,
        source_url: str,
    ) -> None:
        """Load a single relationship into Neo4j.

        Args:
            relationship: The relationship to load.
            source_url: URL of the source document.
        """
        # Build dynamic query based on relationship type
        # We need to handle relationships between different entity types
        rel_type = relationship.relationship_type

        # For stance relationships, source is usually Person (Grigory)
        # For causal relationships, source and target can be any entity type
        query = f"""
        MATCH (source)
        WHERE source.name = $source_name
        MATCH (target)
        WHERE target.name = $target_name
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.reason = $reason,
            r.source_quote = $source_quote,
            r.confidence = $confidence,
            r.source_url = $source_url,
            r.updated_at = datetime()
        RETURN r
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                source_name=relationship.source_entity,
                target_name=relationship.target_entity,
                reason=relationship.reason,
                source_quote=relationship.source_quote,
                confidence=relationship.confidence,
                source_url=source_url,
            )

            # Check if relationship was created
            summary = await result.consume()
            if summary.counters.relationships_created == 0:
                logger.warning(
                    "Relationship not created (nodes may not exist)",
                    source=relationship.source_entity,
                    target=relationship.target_entity,
                    rel_type=rel_type,
                )

    async def load_extraction_result(self, result: ExtractionResult) -> dict:
        """Load a complete extraction result into Neo4j.

        Args:
            result: The extraction result to load.

        Returns:
            Dictionary with counts of loaded entities and relationships.
        """
        entity_count = 0
        relationship_count = 0

        # Load entities first
        for entity in result.entities:
            try:
                await self.load_entity(entity, result.source_url)
                entity_count += 1
            except Exception as e:
                logger.error(
                    "Failed to load entity",
                    entity_name=entity.name,
                    error=str(e),
                )

        # Then load relationships
        for relationship in result.relationships:
            try:
                await self.load_relationship(relationship, result.source_url)
                relationship_count += 1
            except Exception as e:
                logger.error(
                    "Failed to load relationship",
                    source=relationship.source_entity,
                    target=relationship.target_entity,
                    error=str(e),
                )

        return {
            "entities_loaded": entity_count,
            "relationships_loaded": relationship_count,
        }

    async def load_all(
        self,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
        source_url: str = "batch_load",
    ) -> dict:
        """Load deduplicated entities and relationships.

        Args:
            entities: List of entities to load.
            relationships: List of relationships to load.
            source_url: Default source URL for batch loads.

        Returns:
            Dictionary with counts of loaded items.
        """
        # Ensure Person node exists
        await self.create_person_node()

        entity_count = 0
        relationship_count = 0

        # Load entities
        for entity in entities:
            try:
                await self.load_entity(entity, source_url)
                entity_count += 1
            except Exception as e:
                logger.error(
                    "Failed to load entity",
                    entity_name=entity.name,
                    error=str(e),
                )

        logger.info("Entities loaded", count=entity_count)

        # Load relationships
        for relationship in relationships:
            try:
                await self.load_relationship(relationship, source_url)
                relationship_count += 1
            except Exception as e:
                logger.error(
                    "Failed to load relationship",
                    source=relationship.source_entity,
                    target=relationship.target_entity,
                    error=str(e),
                )

        logger.info("Relationships loaded", count=relationship_count)

        return {
            "entities_loaded": entity_count,
            "relationships_loaded": relationship_count,
        }

    async def get_stats(self) -> dict:
        """Get statistics about the knowledge graph.

        Returns:
            Dictionary with node and relationship counts.
        """
        queries = {
            "tools": "MATCH (n:Tool) RETURN count(n) as count",
            "concepts": "MATCH (n:Concept) RETURN count(n) as count",
            "problems": "MATCH (n:Problem) RETURN count(n) as count",
            "persons": "MATCH (n:Person) RETURN count(n) as count",
            "relationships": "MATCH ()-[r]->() RETURN count(r) as count",
        }

        stats = {}
        async with self._driver.session() as session:
            for key, query in queries.items():
                result = await session.run(query)
                record = await result.single()
                stats[key] = record["count"] if record else 0

        stats["total_nodes"] = (
            stats["tools"] + stats["concepts"] + stats["problems"] + stats["persons"]
        )

        return stats

    async def clear_all(self) -> None:
        """Clear all data from the knowledge graph.

        Use with caution - this deletes everything!
        """
        query = "MATCH (n) DETACH DELETE n"

        async with self._driver.session() as session:
            await session.run(query)

        logger.warning("All data cleared from Neo4j")


async def load_to_neo4j(
    entities: list[ExtractedEntity],
    relationships: list[ExtractedRelationship],
    config: Optional[Neo4jConfig] = None,
    uri: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """Convenience function to load data to Neo4j.

    Args:
        entities: List of entities to load.
        relationships: List of relationships to load.
        config: Neo4jConfig instance (optional).
        uri: Neo4j connection URI (overrides config).
        user: Neo4j username (overrides config).
        password: Neo4j password (overrides config).

    Returns:
        Dictionary with counts of loaded items.
    """
    async with Neo4jLoader(
        config=config, uri=uri, user=user, password=password
    ) as loader:
        await loader.create_constraints()
        return await loader.load_all(entities, relationships)
