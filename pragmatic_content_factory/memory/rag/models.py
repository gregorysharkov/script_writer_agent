"""Pydantic models for RAG Constitutional Layer."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Optional
import json

import yaml
from pydantic import BaseModel, Field


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""

    chunk_size: int = 500  # Target chunk size in tokens
    chunk_overlap: int = 50  # Overlap between chunks in tokens


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model: str = "text-embedding-004"  # Gemini embedding model
    dimensions: int = 768  # Embedding vector dimensions
    batch_size: int = 10  # Parallel embedding batch size


class IndexingConfig(BaseModel):
    """Configuration for indexing process."""

    parallel_workers: int = 4  # Number of concurrent workers


class PathsConfig(BaseModel):
    """Configuration for file paths."""

    index_dir: str = "data/faiss_index"  # FAISS index directory
    index_name: str = "pcf-constitutional"  # Index file name


class RAGConfig(BaseModel):
    """Complete RAG configuration loaded from conf/rag_config.yaml."""

    chunking: ChunkingConfig = ChunkingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    indexing: IndexingConfig = IndexingConfig()
    paths: PathsConfig = PathsConfig()

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "RAGConfig":
        """Load configuration from YAML file.

        Args:
            config_path: Path to config file. Defaults to conf/rag_config.yaml.

        Returns:
            RAGConfig instance.
        """
        if config_path is None:
            # Default to conf/rag_config.yaml relative to pragmatic_content_factory
            config_path = (
                Path(__file__).parent.parent.parent / "conf" / "rag_config.yaml"
            )

        if not config_path.exists():
            # Return defaults if config file doesn't exist
            return cls()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def get_config_hash(self) -> str:
        """Generate a hash of the configuration for change detection.

        Returns:
            MD5 hash of the configuration as hex string.
        """
        # Serialize config to JSON-like string for consistent hashing
        config_str = self.model_dump_json(indent=None)
        return hashlib.md5(config_str.encode()).hexdigest()


class DocumentChunk(BaseModel):
    """A chunk of text extracted from a document."""

    text: str = Field(description="The chunk text content")
    source_file: str = Field(description="Path to the source document")
    chunk_index: int = Field(description="Index of this chunk within the document")
    document_type: Literal["static", "dynamic"] = Field(
        description="Whether document is static (read-only) or dynamic (librarian-managed)"
    )
    original_language: str = Field(
        default="unknown", description="ISO 639-1 language code of original text"
    )
    was_translated: bool = Field(
        default=False, description="Whether the text was translated to English"
    )


class DocumentInfo(BaseModel):
    """Information about an indexed document for manifest tracking."""

    file_hash: str = Field(description="MD5 hash of file content")
    chunk_count: int = Field(description="Number of chunks created from this document")
    original_language: str = Field(
        default="unknown", description="Detected source language"
    )
    indexed_at: datetime = Field(default_factory=datetime.utcnow)


class IndexManifest(BaseModel):
    """Manifest tracking indexed documents for incremental updates."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    config_hash: str = Field(description="Hash of RAG config at index time")
    embedding_model: str = Field(description="Embedding model used")
    documents: Annotated[
        dict[str, DocumentInfo],
        Field(default_factory=dict, description="Map of file path to document info"),
    ] = {}
    total_chunks: int = Field(default=0, description="Total number of chunks in index")

    def needs_rebuild(
        self,
        current_config_hash: str,
        current_documents: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """Check if index needs to be rebuilt.

        Args:
            current_config_hash: Hash of current RAG configuration.
            current_documents: Map of file paths to their current content hashes.

        Returns:
            Tuple of (needs_rebuild, list of reasons/changed files).
        """
        reasons = []

        # Check if config changed
        if self.config_hash != current_config_hash:
            reasons.append("Configuration changed")
            return True, reasons

        # Check for new documents
        new_docs = set(current_documents.keys()) - set(self.documents.keys())
        if new_docs:
            reasons.extend([f"New document: {doc}" for doc in new_docs])

        # Check for removed documents
        removed_docs = set(self.documents.keys()) - set(current_documents.keys())
        if removed_docs:
            reasons.extend([f"Removed document: {doc}" for doc in removed_docs])

        # Check for modified documents
        for doc_path, current_hash in current_documents.items():
            if doc_path in self.documents:
                if self.documents[doc_path].file_hash != current_hash:
                    reasons.append(f"Modified document: {doc_path}")

        return len(reasons) > 0, reasons

    @classmethod
    def load(cls, manifest_path: Path) -> Optional["IndexManifest"]:
        """Load manifest from JSON file.

        Args:
            manifest_path: Path to manifest file.

        Returns:
            IndexManifest if file exists, None otherwise.
        """
        if not manifest_path.exists():
            return None

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        return cls(**data)

    def save(self, manifest_path: Path) -> None:
        """Save manifest to JSON file.

        Args:
            manifest_path: Path to save manifest.
        """

        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        self.updated_at = datetime.utcnow()

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)


class RetrievalResult(BaseModel):
    """Result of a RAG retrieval query."""

    query: str = Field(description="The original query text")
    chunks: list[DocumentChunk] = Field(description="Retrieved document chunks")
    scores: list[float] = Field(description="Similarity scores for each chunk")

    @property
    def top_chunk(self) -> Optional[DocumentChunk]:
        """Get the most relevant chunk."""
        return self.chunks[0] if self.chunks else None

    def format_context(self, separator: str = "\n\n---\n\n") -> str:
        """Format all chunks as a single context string.

        Args:
            separator: String to join chunks with.

        Returns:
            Formatted context string.
        """
        return separator.join(chunk.text for chunk in self.chunks)
