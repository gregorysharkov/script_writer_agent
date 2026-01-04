"""Pydantic models for data structures in the content pipeline.

This module provides structured data models for the PCF pipeline:
- ContentBrief: Output of Deep Analyst, input to Voice Architect
- Librarian models: Memory management data structures

Future models (not yet implemented):
- Draft: Output of Voice Architect, input to Ruthless Critic
- Critique: Output of Ruthless Critic
- SocialPosts: Output of Atomizer
- UserFeedback: User feedback at checkpoints
"""

# Content Brief (Deep Analyst output)
from pragmatic_content_factory.models.content_brief import (
    ContentBrief,
    RawInput,
    TalkingPoint,
    SocialCurrency,
    WorldviewAlignment,
    AudiencePainPoint,
)

# Librarian models (memory management)
from pragmatic_content_factory.models.librarian_models import (
    MemoryCandidate,
    MemoryCandidateType,
    ConfidenceLevel,
    MemoryUpdateResult,
    ProcessedURLContent,
    LibrarianInput,
    LibrarianOutput,
)

__all__ = [
    # Content Brief
    "ContentBrief",
    "RawInput",
    "TalkingPoint",
    "SocialCurrency",
    "WorldviewAlignment",
    "AudiencePainPoint",
    # Librarian models
    "MemoryCandidate",
    "MemoryCandidateType",
    "ConfidenceLevel",
    "MemoryUpdateResult",
    "ProcessedURLContent",
    "LibrarianInput",
    "LibrarianOutput",
]
