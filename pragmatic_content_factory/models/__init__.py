"""Pydantic models for data structures in the content pipeline.

This module provides structured data models for the PCF pipeline:
- ContentBrief: Output of Deep Analyst, input to Voice Architect
- DraftScript: Output of Voice Architect, input to Ruthless Critic
- Librarian models: Memory management data structures

Future models (not yet implemented):
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

# Draft Script (Voice Architect output)
from pragmatic_content_factory.models.draft_script import (
    DraftScript,
    ScriptSection,
    Hook,
    CallToAction,
    ContentFormat,
    HookType,
    TargetEmotion,
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
    # Draft Script
    "DraftScript",
    "ScriptSection",
    "Hook",
    "CallToAction",
    "ContentFormat",
    "HookType",
    "TargetEmotion",
    # Librarian models
    "MemoryCandidate",
    "MemoryCandidateType",
    "ConfidenceLevel",
    "MemoryUpdateResult",
    "ProcessedURLContent",
    "LibrarianInput",
    "LibrarianOutput",
]
