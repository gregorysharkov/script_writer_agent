"""Configuration for the Pragmatic Content Factory.

This module provides configuration for the PCF agent pipeline,
including model settings, Neo4j connection, and pipeline parameters.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Neo4jConfig:
    """Configuration for Neo4j Knowledge Graph connection."""

    uri: str = field(
        default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687")
    )
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password")
    )


@dataclass
class RAGConfig:
    """Configuration for RAG Constitutional Layer."""

    index_path: str = field(
        default_factory=lambda: os.getenv("FAISS_INDEX_PATH", "data/faiss_index")
    )
    index_name: str = field(
        default_factory=lambda: os.getenv("FAISS_INDEX_NAME", "pcf-constitutional")
    )


@dataclass
class BrandInfo:
    """Brand and persona information."""

    # Persona
    persona_name: str = "Grigory Sharkov"
    brand_name: str = "The Pragmatic Architect"

    # Target audience
    audience_name: str = "LangChain Survivor"
    audience_description: str = (
        "Data engineers and ML engineers who've been burned by over-engineered "
        "solutions and value pragmatism over hype."
    )

    # Tone and voice
    tone: str = "Confident Pragmatist"
    voice_style: str = "Engineering Stand-up"
    language_mix: str = "Technical jargon mixed with accessible language"

    # Core values
    core_values: list[str] = field(
        default_factory=lambda: [
            "Pragmatism over hype",
            "Simplicity over complexity",
            "Production-readiness",
            "Real results",
            "Battle-tested solutions",
        ]
    )


@dataclass
class PipelineConfig:
    """Configuration for the content pipeline."""

    # Iteration limits
    max_stage_attempts: int = 3  # Maximum retries per stage
    max_critic_iterations: int = 3  # Max Writer-Critic loops

    # Model settings
    analyst_model: str = "gemini-2.5-pro"
    writer_model: str = "gemini-2.5-flash"
    critic_model: str = "gemini-2.5-flash"
    atomizer_model: str = "gemini-2.5-flash"


@dataclass
class PCFConfig:
    """Complete configuration for the Pragmatic Content Factory."""

    # Component configs
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    brand: BrandInfo = field(default_factory=BrandInfo)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # LLM settings
    main_model: str = "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> "PCFConfig":
        """Create configuration from environment variables.

        Returns:
            PCFConfig instance.
        """
        return cls(
            neo4j=Neo4jConfig(),
            rag=RAGConfig(),
            brand=BrandInfo(),
            pipeline=PipelineConfig(),
            main_model=os.getenv("PCF_MODEL", "gemini-2.5-flash"),
        )


# Global configuration instance
config = PCFConfig.from_env()
