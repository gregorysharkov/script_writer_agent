"""Pydantic models for Knowledge Graph configuration and data structures."""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    """Configuration for Neo4j connection."""

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    # Password is not stored in config, only via env var


class QueryConfig(BaseModel):
    """Configuration for query behavior."""

    default_entity_limit: int = 10
    default_worldview_limit: int = 5
    connection_timeout: int = 30


class LabelsConfig(BaseModel):
    """Configuration for Neo4j node labels."""

    person: str = "Person"
    tool: str = "Tool"
    concept: str = "Concept"
    problem: str = "Problem"


class Neo4jConfig(BaseModel):
    """Complete Neo4j configuration loaded from conf/neo4j_config.yaml.

    Sensitive values like password should be set via environment variables.
    """

    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    query: QueryConfig = Field(default_factory=QueryConfig)
    labels: LabelsConfig = Field(default_factory=LabelsConfig)
    stance_relationships: list[str] = Field(
        default_factory=lambda: ["HATES", "PREFERS", "SKEPTICAL_OF", "VALUES"]
    )
    causal_relationships: list[str] = Field(
        default_factory=lambda: ["CAUSES", "ENABLES", "SOLVES", "LEADS_TO"]
    )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Neo4jConfig":
        """Load configuration from YAML file.

        Environment variables override config file values:
        - NEO4J_URI overrides connection.uri
        - NEO4J_USER overrides connection.user

        Args:
            config_path: Path to config file. Defaults to conf/neo4j_config.yaml.

        Returns:
            Neo4jConfig instance.
        """
        if config_path is None:
            # Default to conf/neo4j_config.yaml relative to pragmatic_content_factory
            config_path = (
                Path(__file__).parent.parent.parent / "conf" / "neo4j_config.yaml"
            )

        # Load from file if it exists
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        config = cls(**data)

        # Environment variables override config file
        if os.getenv("NEO4J_URI"):
            config.connection.uri = os.getenv("NEO4J_URI")
        if os.getenv("NEO4J_USER"):
            config.connection.user = os.getenv("NEO4J_USER")

        return config

    def get_password(self) -> str:
        """Get Neo4j password from environment variable.

        Returns:
            Password string.

        Raises:
            ValueError: If NEO4J_PASSWORD is not set.
        """
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        return password

    def get_password_or_default(self, default: str = "password") -> str:
        """Get Neo4j password from environment variable with fallback.

        Args:
            default: Default password if env var not set.

        Returns:
            Password string.
        """
        return os.getenv("NEO4J_PASSWORD", default)


# Singleton config instance
_config: Optional[Neo4jConfig] = None


def get_neo4j_config() -> Neo4jConfig:
    """Get the global Neo4j configuration instance.

    Returns:
        Neo4jConfig instance.
    """
    global _config
    if _config is None:
        _config = Neo4jConfig.load()
    return _config
