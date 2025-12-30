"""FAISS indexer for RAG Constitutional Layer with Gemini embeddings."""

import asyncio
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

import faiss
import google.generativeai as genai
import numpy as np
import structlog
from tqdm import tqdm

from pragmatic_content_factory.memory.rag.models import (
    DocumentChunk,
    DocumentInfo,
    IndexManifest,
    RAGConfig,
)

logger = structlog.get_logger(__name__)


def _configure_genai() -> None:
    """Configure the Gemini API client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    genai.configure(api_key=api_key)


def _compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        MD5 hash as hex string.
    """
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks based on token approximation.

    Uses a simple word-based approximation (1 token ≈ 0.75 words).

    Args:
        text: Text to chunk.
        chunk_size: Target chunk size in tokens.
        chunk_overlap: Overlap between chunks in tokens.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    # Approximate tokens as words * 1.33 (inverse of 0.75 words per token)
    # So chunk_size tokens ≈ chunk_size * 0.75 words
    words_per_chunk = int(chunk_size * 0.75)
    words_overlap = int(chunk_overlap * 0.75)

    # Split into paragraphs first to preserve semantic boundaries
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk_words: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_words = para.split()

        # If paragraph fits in current chunk, add it
        if len(current_chunk_words) + len(para_words) <= words_per_chunk:
            current_chunk_words.extend(para_words)
            current_chunk_words.append("\n\n")  # Preserve paragraph break
        else:
            # Save current chunk if it has content
            if current_chunk_words:
                chunk_text = " ".join(current_chunk_words).strip()
                if chunk_text:
                    chunks.append(chunk_text)

                # Start new chunk with overlap from previous
                if words_overlap > 0 and len(current_chunk_words) > words_overlap:
                    current_chunk_words = current_chunk_words[-words_overlap:]
                else:
                    current_chunk_words = []

            # If paragraph itself is too long, split it
            if len(para_words) > words_per_chunk:
                for i in range(0, len(para_words), words_per_chunk - words_overlap):
                    sub_chunk = para_words[i : i + words_per_chunk]
                    chunks.append(" ".join(sub_chunk))
                current_chunk_words = []
            else:
                current_chunk_words = para_words + ["\n\n"]

    # Don't forget the last chunk
    if current_chunk_words:
        chunk_text = " ".join(current_chunk_words).strip()
        if chunk_text:
            chunks.append(chunk_text)

    return chunks


async def _generate_embeddings(
    texts: list[str],
    model: str = "text-embedding-004",
    batch_size: int = 10,
) -> np.ndarray:
    """Generate embeddings for a list of texts using Gemini.

    Args:
        texts: List of texts to embed.
        model: Gemini embedding model name.
        batch_size: Number of texts to embed in parallel.

    Returns:
        NumPy array of embeddings with shape (len(texts), embedding_dim).
    """
    _configure_genai()

    all_embeddings = []

    # Process in batches with progress bar
    with tqdm(total=len(texts), desc="Generating embeddings", unit="chunk") as pbar:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Generate embeddings for batch
            # Note: genai.embed_content is synchronous, run in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda b=batch: genai.embed_content(
                    model=f"models/{model}",
                    content=b,
                    task_type="retrieval_document",
                ),
            )

            batch_embeddings = results["embedding"]
            all_embeddings.extend(batch_embeddings)
            pbar.update(len(batch))

    return np.array(all_embeddings, dtype=np.float32)


async def generate_query_embedding(
    query: str,
    model: str = "text-embedding-004",
) -> np.ndarray:
    """Generate embedding for a query text.

    Args:
        query: Query text to embed.
        model: Gemini embedding model name.

    Returns:
        NumPy array of shape (embedding_dim,).
    """
    _configure_genai()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: genai.embed_content(
            model=f"models/{model}",
            content=query,
            task_type="retrieval_query",
        ),
    )

    return np.array(result["embedding"], dtype=np.float32)


class RAGIndexer:
    """FAISS indexer for RAG Constitutional Layer."""

    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize the indexer.

        Args:
            config: RAG configuration. Loads from file if not provided.
        """
        self.config = config or RAGConfig.load()
        self._index: Optional[faiss.IndexFlatIP] = None
        self._chunks: list[DocumentChunk] = []
        self._manifest: Optional[IndexManifest] = None

        # Resolve paths relative to pragmatic_content_factory
        self._base_path = Path(__file__).parent.parent.parent
        self._index_dir = self._base_path / self.config.paths.index_dir
        self._index_path = self._index_dir / f"{self.config.paths.index_name}.index"
        self._metadata_path = (
            self._index_dir / f"{self.config.paths.index_name}.metadata.json"
        )
        self._manifest_path = self._index_dir / "index_manifest.json"

    @property
    def index(self) -> Optional[faiss.IndexFlatIP]:
        """Get the FAISS index."""
        return self._index

    @property
    def chunks(self) -> list[DocumentChunk]:
        """Get the indexed chunks."""
        return self._chunks

    def _load_manifest(self) -> Optional[IndexManifest]:
        """Load the index manifest if it exists."""
        return IndexManifest.load(self._manifest_path)

    def _save_manifest(self, manifest: IndexManifest) -> None:
        """Save the index manifest."""
        manifest.save(self._manifest_path)

    def _save_metadata(self) -> None:
        """Save chunk metadata to JSON."""
        self._index_dir.mkdir(parents=True, exist_ok=True)

        metadata = [chunk.model_dump(mode="json") for chunk in self._chunks]
        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            "Saved chunk metadata", path=str(self._metadata_path), count=len(metadata)
        )

    def _load_metadata(self) -> list[DocumentChunk]:
        """Load chunk metadata from JSON."""

        if not self._metadata_path.exists():
            return []

        with open(self._metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        return [DocumentChunk(**chunk) for chunk in metadata]

    def save_index(self) -> None:
        """Save the FAISS index to disk."""
        if self._index is None:
            raise ValueError("No index to save")

        self._index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        self._save_metadata()

        logger.info(
            "Saved FAISS index",
            path=str(self._index_path),
            vectors=self._index.ntotal,
        )

    def load_index(self) -> bool:
        """Load the FAISS index from disk.

        Returns:
            True if index was loaded successfully, False otherwise.
        """
        if not self._index_path.exists():
            logger.warning("Index file not found", path=str(self._index_path))
            return False

        try:
            self._index = faiss.read_index(str(self._index_path))
            self._chunks = self._load_metadata()
            self._manifest = self._load_manifest()

            logger.info(
                "Loaded FAISS index",
                path=str(self._index_path),
                vectors=self._index.ntotal,
                chunks=len(self._chunks),
            )
            return True

        except Exception as e:
            logger.error("Failed to load index", error=str(e))
            return False

    async def build_index(
        self,
        chunks: list[DocumentChunk],
        document_infos: dict[str, DocumentInfo],
    ) -> None:
        """Build FAISS index from document chunks.

        Args:
            chunks: List of document chunks to index.
            document_infos: Map of file paths to document info for manifest.
        """
        if not chunks:
            logger.warning("No chunks to index")
            return

        logger.info("Building FAISS index", chunk_count=len(chunks))

        # Extract texts for embedding
        texts = [chunk.text for chunk in chunks]

        # Generate embeddings
        embeddings = await _generate_embeddings(
            texts,
            model=self.config.embedding.model,
            batch_size=self.config.embedding.batch_size,
        )

        # Normalize embeddings for cosine similarity (using inner product)
        faiss.normalize_L2(embeddings)

        # Create FAISS index
        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(embeddings)
        self._chunks = chunks

        # Create manifest
        self._manifest = IndexManifest(
            created_at=datetime.utcnow(),
            config_hash=self.config.get_config_hash(),
            embedding_model=self.config.embedding.model,
            documents=document_infos,
            total_chunks=len(chunks),
        )

        # Save everything
        self.save_index()
        self._save_manifest(self._manifest)

        logger.info(
            "Index built successfully",
            vectors=self._index.ntotal,
            dimension=dimension,
        )

    def check_needs_rebuild(
        self,
        document_paths: list[Path],
    ) -> tuple[bool, list[str]]:
        """Check if the index needs to be rebuilt.

        Args:
            document_paths: List of document paths to check.

        Returns:
            Tuple of (needs_rebuild, list of reasons).
        """
        # Load existing manifest
        manifest = self._load_manifest()

        if manifest is None:
            return True, ["No existing index found"]

        # Check if index files exist
        if not self._index_path.exists() or not self._metadata_path.exists():
            return True, ["Index files missing"]

        # Compute current document hashes
        current_docs = {}
        for doc_path in document_paths:
            if doc_path.exists():
                # Use relative path for consistency
                rel_path = str(doc_path.relative_to(self._base_path))
                current_docs[rel_path] = _compute_file_hash(doc_path)

        # Get current config hash
        current_config_hash = self.config.get_config_hash()

        # Check against manifest
        return manifest.needs_rebuild(current_config_hash, current_docs)


# Convenience function for creating indexer
def create_indexer(config: Optional[RAGConfig] = None) -> RAGIndexer:
    """Create a RAG indexer instance.

    Args:
        config: Optional RAG configuration.

    Returns:
        RAGIndexer instance.
    """
    return RAGIndexer(config)
