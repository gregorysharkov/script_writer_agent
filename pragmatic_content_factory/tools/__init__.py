"""Shared tools for agents to interact with memory layers.

This module provides ADK-compatible function tools for agents
to query and update RAG (style rules) and Knowledge Graph (worldview).

Usage:
    from pragmatic_content_factory.tools import query_worldview, get_stance

    # Use in agent definition
    agent = Agent(
        name="my_agent",
        tools=[query_worldview, get_stance],
        ...
    )

    # Librarian tools for write operations
    from pragmatic_content_factory.tools import process_urls, add_taboo_term
"""

# RAG tools (for Voice Architect and Ruthless Critic)
from pragmatic_content_factory.tools.rag_tools import (
    query_style_rules,
    query_taboos,
    query_brand_voice,
)

# Knowledge Graph tools (for Deep Analyst)
from pragmatic_content_factory.tools.kg_tools import (
    query_worldview,
    get_stance,
    get_all_stances,
)

# Librarian tools (for memory write operations)
from pragmatic_content_factory.tools.librarian_tools import (
    process_urls,
    add_taboo_term,
    add_style_adjustment,
    add_stance,
)

__all__ = [
    # RAG tools
    "query_style_rules",
    "query_taboos",
    "query_brand_voice",
    # KG tools
    "query_worldview",
    "get_stance",
    "get_all_stances",
    # Librarian tools
    "process_urls",
    "add_taboo_term",
    "add_style_adjustment",
    "add_stance",
]
