"""Entity and relationship extractor using Gemini with structured output."""

import json
import os
from datetime import datetime, timezone
from typing import Literal

import google.generativeai as genai
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Gemini model for entity extraction
DEFAULT_MODEL = "gemini-2.0-flash"


class ExtractedEntity(BaseModel):
    """An entity extracted from source content."""

    name: str = Field(description="The canonical name of the entity")
    entity_type: Literal["Tool", "Concept", "Problem"] = Field(
        description="The type of entity"
    )
    description: str = Field(
        description="A brief description of the entity based on the source"
    )
    source_quote: str = Field(
        description="A direct quote from the source that mentions this entity"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0 to 1"
    )


class ExtractedRelationship(BaseModel):
    """A relationship between entities extracted from source content."""

    source_entity: str = Field(description="The name of the source entity")
    relationship_type: Literal[
        "HATES", "PREFERS", "SKEPTICAL_OF", "VALUES", "CAUSES", "ENABLES", "SOLVES"
    ] = Field(description="The type of relationship")
    target_entity: str = Field(description="The name of the target entity")
    reason: str = Field(description="The reason for this relationship")
    source_quote: str = Field(
        description="A direct quote from the source supporting this relationship"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score from 0 to 1"
    )


class ExtractionResult(BaseModel):
    """Complete extraction result from a source document."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)
    source_url: str = Field(description="The URL of the source document")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def _configure_genai() -> None:
    """Configure the Gemini API client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    genai.configure(api_key=api_key)


EXTRACTION_PROMPT = """Analyze the following text and extract entities and relationships for a knowledge graph about technology, engineering practices, and opinions.

## Entity Types to Extract

1. **Tool**: Technologies, frameworks, libraries, platforms, services
   - Examples: LangChain, Docker, Kubernetes, Python, AWS, Neo4j
   
2. **Concept**: Ideas, principles, methodologies, practices, values
   - Examples: MLOps, DevOps, Clean Code, Reproducibility, Latency, Technical Debt
   
3. **Problem**: Pain points, issues, challenges, anti-patterns
   - Examples: Debugging Nightmare, Vendor Lock-in, Configuration Drift, Hype

## Relationship Types to Extract

1. **HATES**: Strong negative sentiment, criticism, warnings against
2. **PREFERS**: Recommendations, positive sentiment, endorsements
3. **SKEPTICAL_OF**: Cautious stance, qualified criticism, "but..." statements
4. **VALUES**: Emphasized principles, recurring themes, core beliefs
5. **CAUSES**: Causal relationships (X causes Y, X leads to Y)
6. **ENABLES**: Enabling relationships (X enables Y, X makes Y possible)
7. **SOLVES**: Solution relationships (X solves Y, X addresses Y)

## Important Guidelines

- Extract ONLY entities and relationships that are explicitly discussed or strongly implied in the text
- For relationships involving opinions/stances, assume the author is "Grigory" (the brand persona)
- Include direct quotes from the source text to support each extraction
- Assign confidence scores based on how explicit the mention is (1.0 = very explicit, 0.5 = implied)
- Normalize entity names (e.g., "ML Ops" -> "MLOps", "k8s" -> "Kubernetes")
- Focus on technical/engineering entities, not generic business terms

## Output Format

Return a JSON object with this exact structure:
{
    "entities": [
        {
            "name": "EntityName",
            "entity_type": "Tool|Concept|Problem",
            "description": "Brief description based on source",
            "source_quote": "Direct quote from text",
            "confidence": 0.9
        }
    ],
    "relationships": [
        {
            "source_entity": "Grigory",
            "relationship_type": "PREFERS|HATES|SKEPTICAL_OF|VALUES|CAUSES|ENABLES|SOLVES",
            "target_entity": "EntityName",
            "reason": "Why this relationship exists",
            "source_quote": "Direct quote from text",
            "confidence": 0.8
        }
    ]
}

## Text to Analyze

---

Extract all relevant entities and relationships from this text. Return ONLY valid JSON, no other text."""


async def extract_entities_and_relationships(
    text: str,
    source_url: str,
    model_name: str = DEFAULT_MODEL,
) -> ExtractionResult:
    """Extract entities and relationships from text using Gemini.

    Args:
        text: The text content to analyze.
        source_url: The URL of the source document.
        model_name: Gemini model to use.

    Returns:
        ExtractionResult with entities and relationships.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for extraction", source_url=source_url)
        return ExtractionResult(
            entities=[],
            relationships=[],
            source_url=source_url,
        )

    try:
        _configure_genai()
        model = genai.GenerativeModel(model_name)

        # Truncate very long texts to avoid token limits
        max_chars = 50000
        if len(text) > max_chars:
            logger.warning(
                "Truncating text for extraction",
                original_length=len(text),
                truncated_length=max_chars,
            )
            text = text[:max_chars] + "\n\n[Text truncated for processing]"

        # Use string concatenation to avoid issues with curly braces in text
        prompt = EXTRACTION_PROMPT + "\n\n" + text

        logger.info(
            "Extracting entities and relationships",
            source_url=source_url,
            text_length=len(text),
        )

        # Configure for JSON output
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Low temperature for more consistent extraction
        )

        response = model.generate_content(prompt, generation_config=generation_config)

        if not response.text:
            logger.error("Empty response from Gemini", source_url=source_url)
            return ExtractionResult(
                entities=[],
                relationships=[],
                source_url=source_url,
            )

        response_text = response.text.strip()

        # Log raw response for debugging
        logger.debug(
            "Raw Gemini response",
            source_url=source_url,
            response_length=len(response_text),
            response_preview=response_text[:200],
        )

        # Handle markdown-wrapped JSON (```json ... ```)
        if response_text.startswith("```"):
            # Remove markdown code block markers
            lines = response_text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)

        # Parse JSON response
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON response",
                source_url=source_url,
                error=str(e),
                error_position=e.pos,
                response_full=response_text,
            )
            return ExtractionResult(
                entities=[],
                relationships=[],
                source_url=source_url,
            )

        # Convert to Pydantic models with validation
        entities = []
        for entity_data in data.get("entities", []):
            try:
                entity = ExtractedEntity(**entity_data)
                entities.append(entity)
            except Exception as e:
                logger.warning(
                    "Failed to parse entity",
                    entity_data=entity_data,
                    error=str(e),
                )

        relationships = []
        for rel_data in data.get("relationships", []):
            try:
                relationship = ExtractedRelationship(**rel_data)
                relationships.append(relationship)
            except Exception as e:
                logger.warning(
                    "Failed to parse relationship",
                    rel_data=rel_data,
                    error=str(e),
                )

        logger.info(
            "Extraction completed",
            source_url=source_url,
            entity_count=len(entities),
            relationship_count=len(relationships),
        )

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            source_url=source_url,
        )

    except Exception as e:
        logger.exception(
            "Entity extraction failed",
            source_url=source_url,
            error=str(e),
            exc_info=True,
        )
        return ExtractionResult(
            entities=[],
            relationships=[],
            source_url=source_url,
        )


def deduplicate_entities(
    results: list[ExtractionResult],
) -> tuple[list[ExtractedEntity], list[ExtractedRelationship]]:
    """Deduplicate and merge entities from multiple extraction results.

    Args:
        results: List of extraction results from different sources.

    Returns:
        Tuple of (deduplicated_entities, all_relationships).
    """
    # Track entities by normalized name
    entity_map: dict[str, ExtractedEntity] = {}

    for result in results:
        for entity in result.entities:
            # Normalize name for deduplication
            key = entity.name.lower().strip()

            if key not in entity_map:
                entity_map[key] = entity
            else:
                # Keep the one with higher confidence
                existing = entity_map[key]
                if entity.confidence > existing.confidence:
                    entity_map[key] = entity

    # Collect all relationships (they have source attribution)
    all_relationships = []
    for result in results:
        all_relationships.extend(result.relationships)

    # Normalize entity references in relationships
    for rel in all_relationships:
        source_key = rel.source_entity.lower().strip()
        target_key = rel.target_entity.lower().strip()

        # Update to canonical names if available
        if source_key in entity_map:
            rel.source_entity = entity_map[source_key].name
        if target_key in entity_map:
            rel.target_entity = entity_map[target_key].name

    logger.info(
        "Deduplication completed",
        original_entity_count=sum(len(r.entities) for r in results),
        deduplicated_entity_count=len(entity_map),
        relationship_count=len(all_relationships),
    )

    return list(entity_map.values()), all_relationships


async def extract_from_multiple(
    contents: list[tuple[str, str]],  # List of (text, source_url)
    model_name: str = DEFAULT_MODEL,
) -> list[ExtractionResult]:
    """Extract entities from multiple content sources.

    Note: Processed sequentially to avoid rate limiting.

    Args:
        contents: List of (text, source_url) tuples.
        model_name: Gemini model to use.

    Returns:
        List of ExtractionResult objects.
    """
    results = []
    for text, source_url in contents:
        result = await extract_entities_and_relationships(
            text, source_url, model_name=model_name
        )
        results.append(result)
    return results
