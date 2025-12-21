"""Pragmatic Content Factory - An agent ecosystem for personalized content generation."""

__all__ = []

# Conditionally import components that may not exist yet
try:
    from pragmatic_content_factory.agent import root_agent
    __all__.append("root_agent")
except ImportError:
    pass

try:
    from pragmatic_content_factory.setup import seed_knowledge_graph
    __all__.append("seed_knowledge_graph")
except ImportError:
    pass
