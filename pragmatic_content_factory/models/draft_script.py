# pyright: reportAttributeAccessIssue=false
# pylint: disable=E1101
"""Draft Script model - output of the Voice Architect agent.

The Draft Script is the generated content that transforms a Content Brief
into a structured script following brand voice and style rules.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    """Supported content formats."""

    YOUTUBE_SCRIPT = "youtube_script"
    LINKEDIN_POST = "linkedin_post"
    INSTAGRAM_POST = "instagram_post"


class HookType(str, Enum):
    """Types of hooks for content opening.

    These are defined in config.VoiceArchitectConfig for customization.
    """

    QUESTION = "question"
    STATISTIC = "statistic"
    STORY = "story"
    CONTRARIAN = "contrarian"
    PAIN_POINT = "pain_point"


class TargetEmotion(str, Enum):
    """Target emotions that hooks can aim for.

    These are defined in config.VoiceArchitectConfig for customization.
    """

    CURIOSITY = "curiosity"
    FRUSTRATION = "frustration"
    HOPE = "hope"
    RECOGNITION = "recognition"
    SURPRISE = "surprise"


class ScriptSection(BaseModel):
    """A section of the script with optional timing."""

    title: str = Field(description="Section title/heading")
    content: str = Field(description="The actual script content for this section")
    duration_seconds: Optional[int] = Field(
        default=None,
        description="Estimated duration in seconds (for video scripts)",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Production notes or delivery instructions",
    )


class Hook(BaseModel):
    """Opening hook to capture attention."""

    text: str = Field(description="The hook text")
    hook_type: HookType = Field(description="Type of hook used")
    target_emotion: TargetEmotion = Field(description="What emotion this hook targets")


class CallToAction(BaseModel):
    """Call to action for the content."""

    text: str = Field(description="The CTA text")
    action_type: str = Field(
        description="Type of action (subscribe, comment, share, link)"
    )
    placement: str = Field(
        default="end",
        description="Where to place the CTA (intro, middle, end)",
    )


class DraftScript(BaseModel):
    """Structured output from the Voice Architect agent.

    This model represents a draft script generated from a Content Brief,
    following brand voice, tone, and style guidelines from the RAG layer.
    """

    # Core identification
    title: str = Field(description="Final title for the content piece")
    format: ContentFormat = Field(
        default=ContentFormat.YOUTUBE_SCRIPT,
        description="Content format",
    )

    # Hook and opening
    hook: Hook = Field(description="Opening hook to capture attention")

    # Main content structure
    introduction: str = Field(description="Introduction section setting up the topic")
    sections: list[ScriptSection] = Field(
        default_factory=list,
        description="Main content sections",
    )
    conclusion: str = Field(description="Conclusion wrapping up the key points")

    # Engagement elements
    call_to_action: Optional[CallToAction] = Field(
        default=None,
        description="Call to action for the audience",
    )
    quotable_lines: list[str] = Field(
        default_factory=list,
        description="Memorable/shareable one-liners from the script",
    )

    # Metadata
    word_count: int = Field(
        default=0,
        description="Total word count of the script",
    )
    estimated_duration_seconds: Optional[int] = Field(
        default=None,
        description="Estimated total duration in seconds (for video)",
    )

    # Style compliance
    tone_notes: Optional[str] = Field(
        default=None,
        description="Notes on tone and voice used",
    )
    style_rules_applied: list[str] = Field(
        default_factory=list,
        description="List of style rules that were applied",
    )

    # Traceability
    source_brief_title: str = Field(
        description="Title of the Content Brief this was generated from"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this draft was created",
    )

    # Writer notes
    writer_notes: Optional[str] = Field(
        default=None,
        description="Notes from the Voice Architect about the draft",
    )

    def get_full_script(self) -> str:
        """Get the complete script as a single string.

        Returns:
            The full script text.
        """
        parts = [
            f"# {self.title}",
            "",
            "## Hook",
            self.hook.text,
            "",
            "## Introduction",
            self.introduction,
            "",
        ]

        for section in self.sections:
            parts.append(f"## {section.title}")
            parts.append(section.content)
            if section.notes:
                parts.append(f"*[Note: {section.notes}]*")
            parts.append("")

        parts.append("## Conclusion")
        parts.append(self.conclusion)

        if self.call_to_action:
            parts.append("")
            parts.append("## Call to Action")
            parts.append(self.call_to_action.text)

        return "\n".join(parts)

    def format_for_critic(self) -> str:
        """Format the draft for the Ruthless Critic agent.

        Returns:
            Formatted string for critique.
        """
        sections = [
            f"# Draft Script: {self.title}",
            f"**Format:** {self.format.value}",
            f"**Word Count:** {self.word_count}",
        ]

        if self.estimated_duration_seconds:
            minutes = self.estimated_duration_seconds // 60
            seconds = self.estimated_duration_seconds % 60
            sections.append(f"**Estimated Duration:** {minutes}m {seconds}s")

        sections.append("")
        sections.append("---")
        sections.append("")
        sections.append(self.get_full_script())

        if self.quotable_lines:
            sections.append("")
            sections.append("## Quotable Lines")
            for line in self.quotable_lines:
                sections.append(f'- "{line}"')

        if self.style_rules_applied:
            sections.append("")
            sections.append("## Style Rules Applied")
            for rule in self.style_rules_applied:
                sections.append(f"- {rule}")

        if self.tone_notes:
            sections.append("")
            sections.append(f"## Tone Notes\n{self.tone_notes}")

        if self.writer_notes:
            sections.append("")
            sections.append(f"## Writer Notes\n{self.writer_notes}")

        return "\n".join(sections)

    def compute_word_count(self) -> int:
        """Compute and update the word count.

        Returns:
            The total word count.
        """
        total = 0
        total += len(self.hook.text.split())
        total += len(self.introduction.split())
        for section in self.sections:
            total += len(section.content.split())
        total += len(self.conclusion.split())
        if self.call_to_action:
            total += len(self.call_to_action.text.split())

        self.word_count = total
        return total
