"""Knowledge Graph query tools for ADK agents.

These tools provide agents with access to the Knowledge Graph
Worldview Layer for querying stances and entity relationships.
"""

import structlog

from pragmatic_content_factory.memory.knowledge_graph import (
    get_kg_client,
    StanceResult,
    WorldviewContext,
)

logger = structlog.get_logger(__name__)


async def query_worldview(topic: str) -> dict:
    """Query the knowledge graph for worldview context on a topic.

    Use this tool to get Grigory's existing opinions, stances, and
    related concepts for any technology, tool, or concept. This helps
    ensure content aligns with established worldview.

    Args:
        topic: The topic, tool, or concept to query worldview for.
            Examples: "LangChain", "MLOps", "Docker", "Latency"

    Returns:
        Dictionary containing:
        - query: The original query
        - entities: List of relevant entities with their context
        - summary: Human-readable summary of worldview context
    """
    try:
        client = await get_kg_client()
        context: WorldviewContext = await client.query_worldview(topic)

        # Convert to dict for JSON serialization
        result = {
            "query": context.query,
            "summary": context.summary,
            "entities": [],
        }

        for entity in context.entities:
            entity_data = {
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description,
                "stances": [],
                "related": [],
            }

            for stance in entity.stances:
                entity_data["stances"].append(
                    {
                        "stance": stance.stance,
                        "reason": stance.reason,
                        "quote": stance.source_quote,
                    }
                )

            for rel in entity.related_entities:
                entity_data["related"].append(
                    {
                        "name": rel["name"],
                        "type": rel.get("type"),
                        "relationship": rel["relationship"],
                        "direction": rel.get("direction"),
                    }
                )

            result["entities"].append(entity_data)

        logger.info(
            "Worldview query completed",
            topic=topic,
            entities_found=len(result["entities"]),
        )

        return result

    except Exception as e:
        logger.error("Failed to query worldview", topic=topic, error=str(e))
        return {
            "query": topic,
            "summary": f"Failed to query knowledge graph: {str(e)}",
            "entities": [],
            "error": str(e),
        }


async def get_stance(entity_name: str) -> dict:
    """Get Grigory's stance on a specific entity.

    Use this tool to check if Grigory has an established opinion
    on a particular tool, concept, or technology. Returns the
    stance type (HATES, PREFERS, SKEPTICAL_OF, VALUES) with reasoning.

    Args:
        entity_name: Name of the entity to check stance for.
            Examples: "LangChain", "Docker", "Pure Python", "Hype"

    Returns:
        Dictionary containing:
        - entity_name: The queried entity
        - stance: The stance type (or None if no stance exists)
        - reason: Explanation for the stance
        - quote: Supporting quote from source material
        - confidence: Confidence score (0-1)
    """
    try:
        client = await get_kg_client()
        stance: StanceResult = await client.get_stance(entity_name)

        result = {
            "entity_name": stance.entity_name,
            "stance": stance.stance,
            "reason": stance.reason,
            "quote": stance.source_quote,
            "confidence": stance.confidence,
            "has_stance": stance.stance is not None,
        }

        if stance.stance:
            logger.info(
                "Stance found",
                entity=entity_name,
                stance=stance.stance,
            )
        else:
            logger.info(
                "No stance found",
                entity=entity_name,
            )

        return result

    except Exception as e:
        logger.error("Failed to get stance", entity=entity_name, error=str(e))
        return {
            "entity_name": entity_name,
            "stance": None,
            "reason": None,
            "quote": None,
            "confidence": None,
            "has_stance": False,
            "error": str(e),
        }


async def get_all_stances() -> dict:
    """Get all of Grigory's established stances.

    Use this tool to get a complete overview of all opinions
    and stances that should be reflected in content.

    Returns:
        Dictionary containing:
        - stances: List of all stance relationships
        - count: Total number of stances
    """
    try:
        client = await get_kg_client()
        stances = await client.get_all_stances()

        result = {
            "stances": [
                {
                    "entity": s.entity_name,
                    "stance": s.stance,
                    "reason": s.reason,
                    "quote": s.source_quote,
                    "confidence": s.confidence,
                }
                for s in stances
            ],
            "count": len(stances),
        }

        logger.info("Retrieved all stances", count=len(stances))
        return result

    except Exception as e:
        logger.error("Failed to get all stances", error=str(e))
        return {
            "stances": [],
            "count": 0,
            "error": str(e),
        }
