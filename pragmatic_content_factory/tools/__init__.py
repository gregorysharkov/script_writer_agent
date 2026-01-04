"""Shared tools for agents to interact with memory layers.

This module provides ADK-compatible function tools for agents
to query RAG (style rules) and Knowledge Graph (worldview).

Usage:
    from pragmatic_content_factory.tools import query_worldview, get_stance

    # Use in agent definition
    agent = Agent(
        name="my_agent",
        tools=[query_worldview, get_stance],
        ...
    )
"""

__all__ = []

# RAG tools (for Voice Architect and Ruthless Critic)
try:
    from pragmatic_content_factory.tools.rag_tools import (
        query_style_rules,  # noqa: F401
        query_taboos,  # noqa: F401
        query_brand_voice,  # noqa: F401
    )

    __all__.extend(["query_style_rules", "query_taboos", "query_brand_voice"])
except ImportError:
    pass

# Knowledge Graph tools (for Deep Analyst)
try:
    from pragmatic_content_factory.tools.kg_tools import (
        query_worldview,  # noqa: F401
        get_stance,  # noqa: F401
        get_all_stances,  # noqa: F401
    )

    __all__.extend(["query_worldview", "get_stance", "get_all_stances"])
except ImportError:
    pass
