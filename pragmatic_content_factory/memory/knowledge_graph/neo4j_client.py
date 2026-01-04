"""Neo4j client for querying the Knowledge Graph Worldview Layer.

This client provides read-only query access to the knowledge graph,
used by agents (especially Deep Analyst) to contextualize topics
with existing worldview stances and relationships.
"""

from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic import BaseModel, Field
import structlog

from pragmatic_content_factory.memory.knowledge_graph.models import (
    Neo4jConfig,
    get_neo4j_config,
)

logger = structlog.get_logger(__name__)


class StanceResult(BaseModel):
    """Result of a stance query."""

    entity_name: str = Field(description="Name of the entity")
    stance: Optional[str] = Field(
        default=None,
        description="Grigory's stance on this entity (HATES, PREFERS, SKEPTICAL_OF, VALUES)",
    )
    reason: Optional[str] = Field(default=None, description="Reason for the stance")
    source_quote: Optional[str] = Field(
        default=None, description="Supporting quote from source"
    )
    confidence: Optional[float] = Field(
        default=None, description="Confidence score of the relationship"
    )


class EntityContext(BaseModel):
    """Full context for an entity."""

    name: str = Field(description="Entity name")
    entity_type: str = Field(description="Entity type (Tool, Concept, Problem)")
    description: Optional[str] = Field(default=None, description="Entity description")
    source_url: Optional[str] = Field(default=None, description="Source URL")
    stances: list[StanceResult] = Field(
        default_factory=list, description="Stances related to this entity"
    )
    related_entities: list[dict] = Field(
        default_factory=list, description="Related entities and relationships"
    )


class WorldviewContext(BaseModel):
    """Worldview context for a topic query."""

    query: str = Field(description="Original query")
    entities: list[EntityContext] = Field(
        default_factory=list, description="Relevant entities found"
    )
    summary: str = Field(default="", description="Summary of worldview context")


class KnowledgeGraphClient:
    """Client for querying the Knowledge Graph Worldview Layer.

    Provides read-only access to Neo4j for agents to query
    existing stances, relationships, and entity context.

    Configuration is loaded from conf/neo4j_config.yaml with
    environment variable overrides (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).
    """

    _instance: Optional["KnowledgeGraphClient"] = None

    def __init__(
        self,
        config: Optional[Neo4jConfig] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize the KG client.

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
        self._connected = False

    @classmethod
    def get_instance(
        cls,
        config: Optional[Neo4jConfig] = None,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> "KnowledgeGraphClient":
        """Get or create singleton client instance.

        Args:
            config: Neo4jConfig instance.
            uri: Neo4j connection URI.
            user: Neo4j username.
            password: Neo4j password.

        Returns:
            KnowledgeGraphClient instance.
        """
        if cls._instance is None:
            cls._instance = cls(config=config, uri=uri, user=user, password=password)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        if cls._instance and cls._instance._driver:
            # Note: This doesn't close the driver synchronously
            pass
        cls._instance = None

    async def connect(self) -> bool:
        """Establish connection to Neo4j.

        Returns:
            True if connection successful, False otherwise.
        """
        if self._connected and self._driver:
            return True

        try:
            logger.info("Connecting to Neo4j", uri=self.uri)
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            await self._driver.verify_connectivity()
            self._connected = True
            logger.info("Connected to Neo4j successfully")
            return True
        except Exception as e:
            logger.error("Failed to connect to Neo4j", error=str(e))
            self._connected = False
            return False

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Neo4j connection closed")

    async def __aenter__(self) -> "KnowledgeGraphClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def get_stance(self, entity_name: str) -> StanceResult:
        """Get Grigory's stance on a specific entity.

        Args:
            entity_name: Name of the entity to query.

        Returns:
            StanceResult with stance information.
        """
        if not self._connected:
            await self.connect()

        if not self._driver:
            logger.warning("No Neo4j connection available")
            return StanceResult(entity_name=entity_name)

        # Query for stance relationships from Grigory to the entity
        query = """
        MATCH (p:Person {name: 'Grigory'})-[r]->(target)
        WHERE target.name =~ $name_pattern
        AND type(r) IN ['HATES', 'PREFERS', 'SKEPTICAL_OF', 'VALUES']
        RETURN target.name as entity_name,
               type(r) as stance,
               r.reason as reason,
               r.source_quote as source_quote,
               r.confidence as confidence
        LIMIT 1
        """

        try:
            async with self._driver.session() as session:
                # Case-insensitive match
                name_pattern = f"(?i){entity_name}"
                result = await session.run(query, name_pattern=name_pattern)
                record = await result.single()

                if record:
                    return StanceResult(
                        entity_name=record["entity_name"],
                        stance=record["stance"],
                        reason=record["reason"],
                        source_quote=record["source_quote"],
                        confidence=record["confidence"],
                    )

                return StanceResult(entity_name=entity_name)

        except Exception as e:
            logger.error("Failed to query stance", entity=entity_name, error=str(e))
            return StanceResult(entity_name=entity_name)

    async def get_entity_context(
        self, entity_name: str, entity_type: Optional[str] = None
    ) -> Optional[EntityContext]:
        """Get full context for an entity.

        Args:
            entity_name: Name of the entity.
            entity_type: Optional type filter (Tool, Concept, Problem).

        Returns:
            EntityContext if found, None otherwise.
        """
        if not self._connected:
            await self.connect()

        if not self._driver:
            return None

        # Build query based on whether type is specified
        if entity_type:
            node_query = f"""
            MATCH (n:{entity_type})
            WHERE n.name =~ $name_pattern
            RETURN n, labels(n) as labels
            LIMIT 1
            """
        else:
            node_query = """
            MATCH (n)
            WHERE n.name =~ $name_pattern
            AND (n:Tool OR n:Concept OR n:Problem)
            RETURN n, labels(n) as labels
            LIMIT 1
            """

        try:
            async with self._driver.session() as session:
                name_pattern = f"(?i){entity_name}"

                # Get entity node
                result = await session.run(node_query, name_pattern=name_pattern)
                record = await result.single()

                if not record:
                    return None

                node = record["n"]
                labels = record["labels"]
                # Get first non-base label as type
                e_type = next(
                    (
                        label
                        for label in labels
                        if label in ["Tool", "Concept", "Problem"]
                    ),
                    "Unknown",
                )

                # Get stances from Grigory
                stance_query = """
                MATCH (p:Person {name: 'Grigory'})-[r]->(target)
                WHERE target.name = $entity_name
                AND type(r) IN ['HATES', 'PREFERS', 'SKEPTICAL_OF', 'VALUES']
                RETURN type(r) as stance, r.reason as reason,
                       r.source_quote as source_quote, r.confidence as confidence
                """
                stance_result = await session.run(
                    stance_query, entity_name=node["name"]
                )
                stance_records = await stance_result.data()

                stances = [
                    StanceResult(
                        entity_name=node["name"],
                        stance=sr["stance"],
                        reason=sr["reason"],
                        source_quote=sr["source_quote"],
                        confidence=sr["confidence"],
                    )
                    for sr in stance_records
                ]

                # Get related entities
                related_query = """
                MATCH (n)-[r]-(related)
                WHERE n.name = $entity_name
                AND (related:Tool OR related:Concept OR related:Problem OR related:Person)
                RETURN related.name as name, labels(related) as labels,
                       type(r) as relationship, startNode(r).name as from_node
                LIMIT 10
                """
                related_result = await session.run(
                    related_query, entity_name=node["name"]
                )
                related_records = await related_result.data()

                related_entities = [
                    {
                        "name": rr["name"],
                        "type": next(
                            (
                                label
                                for label in rr["labels"]
                                if label in ["Tool", "Concept", "Problem", "Person"]
                            ),
                            "Unknown",
                        ),
                        "relationship": rr["relationship"],
                        "direction": "outgoing"
                        if rr["from_node"] == node["name"]
                        else "incoming",
                    }
                    for rr in related_records
                ]

                return EntityContext(
                    name=node["name"],
                    entity_type=e_type,
                    description=node.get("description"),
                    source_url=node.get("source_url"),
                    stances=stances,
                    related_entities=related_entities,
                )

        except Exception as e:
            logger.error(
                "Failed to get entity context", entity=entity_name, error=str(e)
            )
            return None

    async def query_related_entities(
        self, topic: str, limit: int = 10
    ) -> list[EntityContext]:
        """Find entities and relationships related to a topic.

        Uses text search to find relevant entities.

        Args:
            topic: Topic or keyword to search for.
            limit: Maximum number of entities to return.

        Returns:
            List of EntityContext objects.
        """
        if not self._connected:
            await self.connect()

        if not self._driver:
            return []

        # Search for entities whose name or description contains the topic
        query = """
        MATCH (n)
        WHERE (n:Tool OR n:Concept OR n:Problem)
        AND (n.name =~ $pattern OR n.description =~ $pattern)
        RETURN n.name as name, labels(n) as labels,
               n.description as description, n.source_url as source_url
        LIMIT $limit
        """

        try:
            async with self._driver.session() as session:
                # Case-insensitive partial match
                pattern = f"(?i).*{topic}.*"
                result = await session.run(query, pattern=pattern, limit=limit)
                records = await result.data()

                entities = []
                for record in records:
                    # Get full context for each entity
                    context = await self.get_entity_context(record["name"])
                    if context:
                        entities.append(context)

                return entities

        except Exception as e:
            logger.error("Failed to query related entities", topic=topic, error=str(e))
            return []

    async def query_worldview(self, topic: str) -> WorldviewContext:
        """Query the knowledge graph for worldview context on a topic.

        This is the main method for agents to get relevant context
        including entities, stances, and relationships.

        Args:
            topic: Topic or concept to get worldview context for.

        Returns:
            WorldviewContext with relevant information.
        """
        if not self._connected:
            await self.connect()

        entities = await self.query_related_entities(topic, limit=5)

        # Build summary from found entities
        summary_parts = []
        for entity in entities:
            if entity.stances:
                for stance in entity.stances:
                    if stance.stance and stance.reason:
                        summary_parts.append(
                            f"Grigory {stance.stance.lower().replace('_', ' ')} "
                            f"{entity.name}: {stance.reason}"
                        )
            if entity.related_entities:
                relationships = [
                    f"{entity.name} {rel['relationship']} {rel['name']}"
                    for rel in entity.related_entities[:3]
                ]
                if relationships:
                    summary_parts.append(f"Relationships: {', '.join(relationships)}")

        summary = (
            "\n".join(summary_parts)
            if summary_parts
            else "No worldview context found for this topic."
        )

        return WorldviewContext(
            query=topic,
            entities=entities,
            summary=summary,
        )

    async def get_all_stances(self) -> list[StanceResult]:
        """Get all of Grigory's stances.

        Returns:
            List of all stance relationships.
        """
        if not self._connected:
            await self.connect()

        if not self._driver:
            return []

        query = """
        MATCH (p:Person {name: 'Grigory'})-[r]->(target)
        WHERE type(r) IN ['HATES', 'PREFERS', 'SKEPTICAL_OF', 'VALUES']
        RETURN target.name as entity_name,
               type(r) as stance,
               r.reason as reason,
               r.source_quote as source_quote,
               r.confidence as confidence
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(query)
                records = await result.data()

                return [
                    StanceResult(
                        entity_name=r["entity_name"],
                        stance=r["stance"],
                        reason=r["reason"],
                        source_quote=r["source_quote"],
                        confidence=r["confidence"],
                    )
                    for r in records
                ]

        except Exception as e:
            logger.error("Failed to get all stances", error=str(e))
            return []


# Module-level singleton instance
_client: Optional[KnowledgeGraphClient] = None


async def get_kg_client() -> KnowledgeGraphClient:
    """Get the global KG client instance.

    Returns:
        KnowledgeGraphClient instance.
    """
    global _client
    if _client is None:
        _client = KnowledgeGraphClient.get_instance()
        await _client.connect()
    return _client


# Convenience functions for direct use
async def get_stance(entity_name: str) -> StanceResult:
    """Get Grigory's stance on an entity.

    Args:
        entity_name: Name of the entity.

    Returns:
        StanceResult with stance information.
    """
    client = await get_kg_client()
    return await client.get_stance(entity_name)


async def query_worldview(topic: str) -> WorldviewContext:
    """Query worldview context for a topic.

    Args:
        topic: Topic to query.

    Returns:
        WorldviewContext with relevant information.
    """
    client = await get_kg_client()
    return await client.query_worldview(topic)
