"""Content Brief model - output of the Deep Analyst agent.

The Content Brief is a structured representation of analyzed raw input,
containing key insights, pain points, social currency, and talking points
that will be used by downstream agents to create content.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AudiencePainPoint(str, Enum):
    """Standard pain points for the target audience (LangChain Survivor)."""

    LATENCY = "latency"
    DEBUGGING_NIGHTMARE = "debugging_nightmare"
    VENDOR_LOCK_IN = "vendor_lock_in"
    COMPLEXITY_OVERHEAD = "complexity_overhead"
    COST_EXPLOSION = "cost_explosion"
    REPRODUCIBILITY = "reproducibility"
    OBSERVABILITY = "observability"
    DEPLOYMENT_HELL = "deployment_hell"
    TECH_DEBT = "tech_debt"
    HYPE_FATIGUE = "hype_fatigue"
    OTHER = "other"


class TalkingPoint(BaseModel):
    """A single talking point for the content brief."""

    title: str = Field(description="Brief title/headline for this point")
    key_message: str = Field(description="The main message to convey")
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Facts, examples, or quotes supporting this point",
    )
    audience_hook: Optional[str] = Field(
        default=None,
        description="Why this matters to the target audience",
    )
    worldview_alignment: Optional[str] = Field(
        default=None,
        description="How this aligns with Grigory's established worldview",
    )


class SocialCurrency(BaseModel):
    """Social currency element - something worth sharing."""

    angle: str = Field(description="The shareable/quotable angle")
    format_suggestion: str = Field(
        description="Suggested format (hot take, statistic, metaphor, story, etc.)"
    )
    virality_potential: str = Field(
        description="What makes this shareable (contrarian, surprising, relatable, useful)"
    )


class WorldviewAlignment(BaseModel):
    """Alignment with established worldview from Knowledge Graph."""

    entity: str = Field(description="The entity (tool, concept, problem)")
    stance: Optional[str] = Field(
        default=None,
        description="Grigory's stance (HATES, PREFERS, SKEPTICAL_OF, VALUES)",
    )
    reason: Optional[str] = Field(default=None, description="Reason for the stance")
    content_implication: str = Field(
        description="How this should influence the content"
    )


class ContentBrief(BaseModel):
    """Structured output from the Deep Analyst agent.

    This model captures the analysis of raw input material,
    providing a structured brief for the Voice Architect
    to use when generating draft content.
    """

    # Core identification
    title: str = Field(description="Working title for the content piece")
    content_type: str = Field(
        default="youtube_script",
        description="Type of content (youtube_script, linkedin_post, etc.)",
    )

    # Key insight extraction
    key_insight: str = Field(
        description="The core idea or insight extracted from the raw material"
    )
    insight_strength: str = Field(
        description="What makes this insight compelling (novelty, utility, controversy)"
    )

    # Target audience analysis
    pain_points_addressed: list[AudiencePainPoint] = Field(
        default_factory=list,
        description="Which audience pain points this content addresses",
    )
    pain_point_details: dict[str, str] = Field(
        default_factory=dict,
        description="Detailed explanation of how each pain point is addressed",
    )

    # Social currency
    social_currency: list[SocialCurrency] = Field(
        default_factory=list,
        description="Shareable/quotable angles for viral potential",
    )

    # Structured talking points
    talking_points: list[TalkingPoint] = Field(
        default_factory=list,
        description="Structured points to cover in the content",
    )

    # Worldview alignment
    worldview_context: list[WorldviewAlignment] = Field(
        default_factory=list,
        description="Relevant stances and alignments from knowledge graph",
    )

    # Metadata
    raw_input_summary: str = Field(
        description="Brief summary of the original raw input"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this brief was created",
    )

    # Analyst notes
    analyst_notes: Optional[str] = Field(
        default=None,
        description="Additional notes or recommendations from the analyst",
    )
    suggested_angle: Optional[str] = Field(
        default=None,
        description="Recommended angle or approach for the content",
    )

    def format_for_writer(self) -> str:
        """Format the brief for the Voice Architect agent.

        Returns:
            Formatted string representation of the brief.
        """
        sections = [
            f"# Content Brief: {self.title}",
            f"\n## Key Insight\n{self.key_insight}",
            f"**Strength:** {self.insight_strength}",
        ]

        if self.pain_points_addressed:
            sections.append("\n## Pain Points Addressed")
            for pp in self.pain_points_addressed:
                detail = (
                    self.pain_point_details[pp.value]
                    if hasattr(self.pain_point_details, "__getitem__")
                    and pp.value in self.pain_point_details
                    else ""
                )
                sections.append(f"- **{pp.value}**: {detail}")

        if self.social_currency:
            sections.append("\n## Social Currency")
            for sc in self.social_currency:
                sections.append(
                    f"- **{sc.format_suggestion}**: {sc.angle}\n  "
                    f"  *Virality: {sc.virality_potential}*"
                )

        if self.talking_points:
            sections.append("\n## Talking Points")
            for i, tp in enumerate(self.talking_points, 1):
                sections.append(f"\n### {i}. {tp.title}")
                sections.append(f"{tp.key_message}")
                if tp.supporting_evidence:
                    sections.append("**Evidence:**")
                    for ev in tp.supporting_evidence:
                        sections.append(f"  - {ev}")
                if tp.audience_hook:
                    sections.append(f"**Why it matters:** {tp.audience_hook}")
                if tp.worldview_alignment:
                    sections.append(f"**Worldview:** {tp.worldview_alignment}")

        if self.worldview_context:
            sections.append("\n## Worldview Context")
            for wv in self.worldview_context:
                stance_str = f"({wv.stance})" if wv.stance else ""
                sections.append(
                    f"- **{wv.entity}** {stance_str}: {wv.content_implication}"
                )

        if self.suggested_angle:
            sections.append(f"\n## Suggested Angle\n{self.suggested_angle}")

        if self.analyst_notes:
            sections.append(f"\n## Analyst Notes\n{self.analyst_notes}")

        return "\n".join(sections)


class RawInput(BaseModel):
    """Raw input to the Deep Analyst agent."""

    content: str = Field(description="The raw text content (transcript, ideas, notes)")
    source_type: str = Field(
        default="text",
        description="Source type (transcript, notes, idea, etc.)",
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context about the input",
    )
    target_content_type: str = Field(
        default="youtube_script",
        description="What type of content to create from this input",
    )
