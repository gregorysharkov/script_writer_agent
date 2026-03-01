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
class HookType:
    """Definition of a hook type for content opening."""

    name: str
    description: str
    example: str


@dataclass
class VoiceArchitectConfig:
    """Configuration for the Voice Architect agent."""

    # Hook types available for content creation
    hook_types: list[HookType] = field(
        default_factory=lambda: [
            HookType(
                name="question",
                description="Opens with a provocative question that resonates with audience pain",
                example="Why does every LLM app end up with 10x the code it needs?",
            ),
            HookType(
                name="statistic",
                description="Opens with a surprising or compelling data point",
                example="73% of ML projects never make it to production. Here's why.",
            ),
            HookType(
                name="story",
                description="Opens with a relatable personal anecdote",
                example="Last week I spent 4 hours debugging a LangChain chain. The fix was 3 lines.",
            ),
            HookType(
                name="contrarian",
                description="Opens with a stance that challenges conventional wisdom",
                example="Everyone's building with LangChain. Here's why I'm not.",
            ),
            HookType(
                name="pain_point",
                description="Opens by directly naming a frustration the audience feels",
                example="You know that feeling when your 'simple' LLM wrapper turns into 2000 lines of framework code?",
            ),
        ]
    )

    # Target emotions hooks can aim for
    target_emotions: list[str] = field(
        default_factory=lambda: [
            "curiosity",
            "frustration",
            "hope",
            "recognition",
            "surprise",
        ]
    )

    def get_hook_type_names(self) -> list[str]:
        """Get list of valid hook type names."""
        return [h.name for h in self.hook_types]

    def format_hook_types_for_prompt(self) -> str:
        """Format hook types as markdown for agent instruction."""
        lines = ["Hook Types:"]
        for hook in self.hook_types:
            lines.append(f'- **{hook.name.title()}**: "{hook.example}"')
            lines.append(f"  {hook.description}")
        return "\n".join(lines)


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
    voice_architect: VoiceArchitectConfig = field(default_factory=VoiceArchitectConfig)

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
            voice_architect=VoiceArchitectConfig(),
            main_model=os.getenv("PCF_MODEL", "gemini-2.5-flash"),
        )


# Global configuration instance
config = PCFConfig.from_env()
