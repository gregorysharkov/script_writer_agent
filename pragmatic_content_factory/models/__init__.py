"""Pydantic models for data structures in the content pipeline.

This module provides structured data models for the PCF pipeline:
- ContentBrief: Output of Deep Analyst, input to Voice Architect
- Draft: Output of Voice Architect, input to Ruthless Critic
- Critique: Output of Ruthless Critic
- SocialPosts: Output of Atomizer
- UserFeedback: User feedback at checkpoints
"""

__all__ = []

# Content Brief (Deep Analyst output)
try:
    from pragmatic_content_factory.models.content_brief import (
        ContentBrief,
        RawInput,
        TalkingPoint,
        SocialCurrency,
        WorldviewAlignment,
        AudiencePainPoint,
    )

    __all__.extend(
        [
            "ContentBrief",
            "RawInput",
            "TalkingPoint",
            "SocialCurrency",
            "WorldviewAlignment",
            "AudiencePainPoint",
        ]
    )
except ImportError:
    pass

# Draft (Voice Architect output)
try:
    from pragmatic_content_factory.models.draft import Draft

    __all__.append("Draft")
except ImportError:
    pass

# Critique (Ruthless Critic output)
try:
    from pragmatic_content_factory.models.critique import Critique, CritiqueResult

    __all__.extend(["Critique", "CritiqueResult"])
except ImportError:
    pass

# Social Posts (Atomizer output)
try:
    from pragmatic_content_factory.models.social_posts import SocialPosts

    __all__.append("SocialPosts")
except ImportError:
    pass

# User Feedback (checkpoint input)
try:
    from pragmatic_content_factory.models.feedback import UserFeedback

    __all__.append("UserFeedback")
except ImportError:
    pass
