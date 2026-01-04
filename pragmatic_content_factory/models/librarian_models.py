"""Pydantic models for Librarian agent feedback analysis and memory management.

This module distinguishes between:
- Learning signals (what is DETECTED from user feedback)
- Processed content (what is actually STORED in memory)

For URLs, the detected signal is the URL itself, but what gets stored
is the extracted content (entities, relationships) after processing.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class MemoryCandidateType(str, Enum):
    """Types of learning signals the Librarian can detect."""

    URL = "url"  # URL to fetch, process, and extract entities from
    TABOO_TERM = "taboo_term"  # Term to add to taboo list
    STANCE = "stance"  # Stance/opinion to add to knowledge graph
    STYLE_ADJUSTMENT = "style_adjustment"  # Style preference to record


class ConfidenceLevel(str, Enum):
    """Confidence levels for detected learning signals."""

    HIGH = "high"  # Explicit instruction, execute immediately
    MEDIUM = "medium"  # Inferred preference, confirm with user
    LOW = "low"  # Ambiguous signal, log but don't act


class MemoryCandidate(BaseModel):
    """A learning signal detected from user feedback.

    NOTE: This represents what was DETECTED, not what will be STORED.

    For URLs:
    - detected_value contains the URL to fetch
    - The actual content (article, PDF, transcript) is fetched and processed
    - Entities and relationships are extracted via LLM
    - Only the extracted knowledge is stored in the Knowledge Graph

    For taboo terms, stances, and style adjustments:
    - detected_value contains the term/description to store directly
    """

    candidate_type: MemoryCandidateType = Field(
        description="Type of learning signal (url, taboo_term, stance, style_adjustment)"
    )
    detected_value: str = Field(
        description=(
            "The detected value that triggered this signal. "
            "For URLs: the URL to fetch and process (content will be extracted). "
            "For taboo terms: the term to prohibit. "
            "For stances: description of the stance. "
            "For style adjustments: the style preference."
        )
    )
    source_text: str = Field(
        description="Original user text that triggered detection of this signal"
    )
    confidence: ConfidenceLevel = Field(
        description="Confidence level for this detection"
    )
    reason: str = Field(
        description="Explanation of why this was detected as a learning signal"
    )
    detected_at: datetime = Field(
        default_factory=_utc_now, description="When this signal was detected"
    )

    # Optional fields for specific candidate types
    stance_type: Optional[Literal["HATES", "PREFERS", "SKEPTICAL_OF", "VALUES"]] = (
        Field(default=None, description="For stance signals: the type of stance")
    )
    target_entity: Optional[str] = Field(
        default=None, description="For stance signals: the entity the stance is about"
    )


class ProcessedURLContent(BaseModel):
    """Content extracted from a URL for storage in knowledge graph.

    When a URL is processed, this model captures what was actually
    extracted and stored, not just the raw URL.
    """

    source_url: str = Field(description="Original URL the content was fetched from")
    title: Optional[str] = Field(
        default=None, description="Title of the fetched content"
    )
    content_type: Literal["webpage", "pdf", "youtube"] = Field(
        description="Type of content that was fetched"
    )
    was_translated: bool = Field(
        default=False, description="Whether the content was translated to English"
    )
    original_language: Optional[str] = Field(
        default=None, description="Original language if translated"
    )
    entities_extracted: list[str] = Field(
        default_factory=list, description="Names of entities extracted and stored in KG"
    )
    relationships_extracted: list[str] = Field(
        default_factory=list,
        description="Descriptions of relationships extracted and stored in KG",
    )
    processed_at: datetime = Field(
        default_factory=_utc_now, description="When this content was processed"
    )


class MemoryUpdateResult(BaseModel):
    """Result of a memory update operation performed by the Librarian.

    For URL processing, this includes details of what content was
    extracted and stored (not just the URL itself).
    """

    update_type: str = Field(
        description="Type of update performed (url_processed, taboo_added, stance_added, style_adjusted)"
    )
    success: bool = Field(description="Whether the update was successful")
    details: str = Field(description="Human-readable description of what was updated")
    requires_confirmation: bool = Field(
        default=False,
        description="Whether this update requires user confirmation before execution",
    )
    error: Optional[str] = Field(
        default=None, description="Error message if the update failed"
    )
    updated_at: datetime = Field(
        default_factory=_utc_now, description="When this update was performed"
    )

    # Metrics for the update
    entities_added: int = Field(
        default=0, description="Number of entities added to knowledge graph"
    )
    relationships_added: int = Field(
        default=0, description="Number of relationships added to knowledge graph"
    )
    chunks_added: int = Field(
        default=0, description="Number of chunks added to RAG index"
    )

    # For URL processing, details of what was extracted
    processed_content: Optional[ProcessedURLContent] = Field(
        default=None, description="For URL updates: details of extracted content"
    )


class LibrarianInput(BaseModel):
    """Input to the Librarian agent for feedback analysis.

    Contains user feedback, agent outputs, and context for the Librarian
    to analyze and determine what should be stored in memory.
    """

    user_message: Optional[str] = Field(
        default=None, description="The user's feedback or instruction message"
    )
    agent_output: Optional[str] = Field(
        default=None, description="Output from previous agent (e.g., content brief)"
    )
    urls_to_process: list[str] = Field(
        default_factory=list,
        description="Explicit URLs to process into knowledge graph",
    )
    context: Optional[str] = Field(
        default=None, description="Additional context for the Librarian"
    )


class LibrarianOutput(BaseModel):
    """Output from the Librarian agent after processing feedback.

    Summarizes all memory candidates detected and updates performed.
    """

    candidates_detected: list[MemoryCandidate] = Field(
        default_factory=list, description="All memory candidates detected from input"
    )
    updates_performed: list[MemoryUpdateResult] = Field(
        default_factory=list, description="Results of memory updates that were executed"
    )
    pending_confirmations: list[MemoryCandidate] = Field(
        default_factory=list, description="Candidates awaiting user confirmation"
    )
    summary: str = Field(
        default="", description="Human-readable summary of Librarian actions"
    )
