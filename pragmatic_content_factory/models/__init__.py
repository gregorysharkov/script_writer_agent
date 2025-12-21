"""Pydantic models for data structures in the content pipeline."""

__all__ = []

# Conditionally import models that may not be implemented yet
try:
    from pragmatic_content_factory.models.content_brief import ContentBrief
    __all__.append("ContentBrief")
except ImportError:
    pass

try:
    from pragmatic_content_factory.models.draft import Draft
    __all__.append("Draft")
except ImportError:
    pass

try:
    from pragmatic_content_factory.models.critique import Critique, CritiqueResult
    __all__.extend(["Critique", "CritiqueResult"])
except ImportError:
    pass

try:
    from pragmatic_content_factory.models.social_posts import SocialPosts
    __all__.append("SocialPosts")
except ImportError:
    pass

try:
    from pragmatic_content_factory.models.feedback import UserFeedback
    __all__.append("UserFeedback")
except ImportError:
    pass
