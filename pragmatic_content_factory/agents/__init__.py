"""The Crew - Specialized agents for content generation pipeline.

Currently implemented:
- deep_analyst: Extracts insights from raw content
- voice_architect: Generates draft scripts from content briefs
- librarian: Manages memory updates from feedback

Future agents (not yet implemented):
- ruthless_critic: Validates against brand rules
- atomizer: Creates platform-specific content
"""

from pragmatic_content_factory.agents.deep_analyst import deep_analyst
from pragmatic_content_factory.agents.voice_architect import voice_architect
from pragmatic_content_factory.agents.librarian import librarian

__all__ = [
    "deep_analyst",
    "voice_architect",
    "librarian",
]
