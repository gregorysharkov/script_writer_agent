"""The Crew - Specialized agents for content generation pipeline.

Currently implemented:
- deep_analyst: Extracts insights from raw content
- librarian: Manages memory updates from feedback

Future agents (not yet implemented):
- voice_architect: Generates draft scripts
- ruthless_critic: Validates against brand rules
- atomizer: Creates platform-specific content
"""

from pragmatic_content_factory.agents.deep_analyst import deep_analyst
from pragmatic_content_factory.agents.librarian import librarian

__all__ = [
    "deep_analyst",
    "librarian",
]
