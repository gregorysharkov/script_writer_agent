"""Utilities for integrating channel information into agent instructions"""

from .config import ChannelInfo


def generate_channel_context(channel_info: ChannelInfo) -> str:
    """Generate a formatted channel context section for agent instructions"""

    if not any(
        [
            channel_info.channel_name,
            channel_info.creator_name,
            channel_info.target_audience,
            channel_info.content_style,
            channel_info.expertise_areas,
        ]
    ):
        return ""

    context_parts = []

    # Basic Channel Information
    if channel_info.channel_name or channel_info.creator_name:
        context_parts.append("## CHANNEL INFORMATION")
        if channel_info.channel_name:
            context_parts.append(f"- **Channel Name**: {channel_info.channel_name}")
        if channel_info.creator_name:
            context_parts.append(f"- **Creator**: {channel_info.creator_name}")
        if channel_info.channel_description:
            context_parts.append(
                f"- **Channel Description**: {channel_info.channel_description}"
            )

    # Target Audience & Content Style
    if channel_info.target_audience or channel_info.content_style:
        context_parts.append("\n## CONTENT GUIDELINES")
        if channel_info.target_audience:
            context_parts.append(
                f"- **Target Audience**: {channel_info.target_audience}"
            )
        if channel_info.content_style:
            context_parts.append(f"- **Content Style**: {channel_info.content_style}")
        if channel_info.tone_of_voice:
            context_parts.append(f"- **Tone of Voice**: {channel_info.tone_of_voice}")
        if channel_info.preferred_video_length:
            context_parts.append(
                f"- **Preferred Video Length**: {channel_info.preferred_video_length}"
            )

    # Creator Expertise & Branding
    if channel_info.expertise_areas or channel_info.creator_background:
        context_parts.append("\n## CREATOR EXPERTISE & BRANDING")
        if channel_info.expertise_areas:
            expertise_list = ", ".join(channel_info.expertise_areas)
            context_parts.append(f"- **Areas of Expertise**: {expertise_list}")
        if channel_info.creator_background:
            context_parts.append(
                f"- **Creator Background**: {channel_info.creator_background}"
            )
        if channel_info.unique_value_proposition:
            context_parts.append(
                f"- **Unique Value Proposition**: {channel_info.unique_value_proposition}"
            )
        if channel_info.personal_story:
            context_parts.append(
                f"- **Personal Story/Connection**: {channel_info.personal_story}"
            )

    # Engagement & Production
    if channel_info.call_to_action_style or channel_info.engagement_preferences:
        context_parts.append("\n## ENGAGEMENT & PRODUCTION PREFERENCES")
        if channel_info.call_to_action_style:
            context_parts.append(
                f"- **Call-to-Action Style**: {channel_info.call_to_action_style}"
            )
        if channel_info.engagement_preferences:
            context_parts.append(
                f"- **Engagement Preferences**: {channel_info.engagement_preferences}"
            )
        if channel_info.visual_style_notes:
            context_parts.append(
                f"- **Visual Style Notes**: {channel_info.visual_style_notes}"
            )
        if channel_info.production_constraints:
            context_parts.append(
                f"- **Production Constraints**: {channel_info.production_constraints}"
            )

    if context_parts:
        context_parts.append("\n## INTEGRATION REQUIREMENTS")
        context_parts.append(
            "- **CRITICAL**: All content must align with the above channel information"
        )
        context_parts.append(
            "- Incorporate the creator's expertise and background naturally"
        )
        context_parts.append(
            "- Ensure the tone and style match the channel's established voice"
        )
        context_parts.append("- Consider the target audience in all content decisions")
        context_parts.append("- Respect production constraints and preferences")
        context_parts.append("")

        return "\n".join(context_parts)

    return ""


def get_channel_aware_instruction(
    base_instruction: str, channel_info: ChannelInfo
) -> str:
    """Combine base instruction with channel context"""
    channel_context = generate_channel_context(channel_info)

    if channel_context:
        return f"{channel_context}\n{base_instruction}"

    return base_instruction
