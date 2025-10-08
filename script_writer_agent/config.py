from dataclasses import dataclass, field
from typing import List


@dataclass
class ChannelInfo:
    """Channel information and creator preferences"""

    # Basic Channel Info
    channel_name: str = "ML Ops Navigator"
    creator_name: str = "Grigory Sharkov"
    channel_description: str = "A channel about machine learning operations and data engineering. I am helping people to become better in this field."
    target_audience: str = "Data engineers and machine learning engineers, looking for guidance and practical tips."

    # Content Preferences
    content_style: str = (
        "educational"  # e.g., "educational", "entertaining", "professional", "casual"
    )
    tone_of_voice: str = "conversational"  # e.g., "friendly", "authoritative", "conversational", "technical"
    expertise_areas: List[str] = field(
        default_factory=lambda: [
            "machine learning operations",
            "data engineering",
            "data science",
            "artificial intelligence",
        ]
    )  # e.g., ["cybersecurity", "AI", "programming"]

    # Personal Branding
    unique_value_proposition: str = "A shared experience of building production ready systems that really work."  # What makes this channel unique
    creator_background: str = "ML and AI engineer with 7+ years of experience in building production ready systems. Switched from business to tech in 2019."  # Professional background, credentials
    personal_story: str = ""  # Personal elements that build trust/connection

    # Content Guidelines
    preferred_video_length: str = (
        "10-15 minutes"  # e.g., "8-12 minutes", "short-form", "long-form"
    )
    call_to_action_style: str = "Event the best performing model is worth nothing until put into production."  # How to end videos, what to ask viewers
    engagement_preferences: str = ""  # How to interact with audience

    # Technical Preferences
    visual_style_notes: str = ""  # Preferences for visuals, graphics, etc.
    production_constraints: str = ""  # Equipment, budget, time constraints


@dataclass
class ScriptWriterAgentConfig:
    """Configuration for the script writer agent"""

    main_model: str = "gemini-2.5-flash"
    max_research_iterations: int = (
        1  # Number of retry attempts for researcher (1 = no retries, just one attempt)
    )
    max_search_queries: int = (
        6  # Maximum number of search queries per research session (4-6 recommended)
    )
    channel_info: ChannelInfo = field(default_factory=ChannelInfo)


config = ScriptWriterAgentConfig()
