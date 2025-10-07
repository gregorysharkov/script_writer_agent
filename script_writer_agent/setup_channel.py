"""
Channel Setup Utility

This module provides utilities to configure your channel information for personalized script generation.
Run this script to set up your channel preferences, or import and use the functions programmatically.
"""

from .config import config, ChannelInfo


def setup_channel_interactive():
    """Interactive setup for channel information"""
    print("🎬 Script Writer Agent - Channel Setup")
    print("=" * 50)
    print(
        "Let's configure your channel information for personalized script generation.\n"
    )

    # Basic Channel Info
    print("📺 BASIC CHANNEL INFORMATION")
    channel_name = input("Channel Name: ").strip()
    creator_name = input("Your Name (Creator): ").strip()
    channel_description = input("Channel Description (brief): ").strip()
    target_audience = input(
        "Target Audience (e.g., 'software developers', 'cybersecurity professionals'): "
    ).strip()

    # Content Preferences
    print("\n🎨 CONTENT PREFERENCES")
    print(
        "Content Style options: educational, entertaining, professional, casual, technical, etc."
    )
    content_style = input("Content Style: ").strip()

    print(
        "Tone of Voice options: friendly, authoritative, conversational, technical, humorous, etc."
    )
    tone_of_voice = input("Tone of Voice: ").strip()

    print("Expertise Areas (comma-separated, e.g., 'cybersecurity, AI, programming'): ")
    expertise_input = input("Areas of Expertise: ").strip()
    expertise_areas = [
        area.strip() for area in expertise_input.split(",") if area.strip()
    ]

    # Personal Branding
    print("\n🌟 PERSONAL BRANDING")
    unique_value_proposition = input("What makes your channel unique?: ").strip()
    creator_background = input("Your professional background/credentials: ").strip()
    personal_story = input(
        "Personal story/connection with audience (optional): "
    ).strip()

    # Content Guidelines
    print("\n📋 CONTENT GUIDELINES")
    print(
        "Video Length options: '5-8 minutes', '10-15 minutes', 'short-form', 'long-form', etc."
    )
    preferred_video_length = input("Preferred Video Length: ").strip()

    call_to_action_style = input(
        "How do you typically end videos/ask for engagement?: "
    ).strip()
    engagement_preferences = input(
        "How do you prefer to interact with your audience?: "
    ).strip()

    # Technical Preferences
    print("\n🎥 TECHNICAL PREFERENCES")
    visual_style_notes = input("Visual style preferences (optional): ").strip()
    production_constraints = input(
        "Production constraints (equipment, budget, time, etc.): "
    ).strip()

    # Create ChannelInfo object
    channel_info = ChannelInfo(
        channel_name=channel_name,
        creator_name=creator_name,
        channel_description=channel_description,
        target_audience=target_audience,
        content_style=content_style,
        tone_of_voice=tone_of_voice,
        expertise_areas=expertise_areas,
        unique_value_proposition=unique_value_proposition,
        creator_background=creator_background,
        personal_story=personal_story,
        preferred_video_length=preferred_video_length,
        call_to_action_style=call_to_action_style,
        engagement_preferences=engagement_preferences,
        visual_style_notes=visual_style_notes,
        production_constraints=production_constraints,
    )

    # Update config
    config.channel_info = channel_info

    print("\n✅ Channel information configured successfully!")
    print("\nYour channel setup:")
    print_channel_summary(channel_info)

    return channel_info


def setup_channel_programmatic(**kwargs):
    """
    Programmatically set up channel information

    Args:
        **kwargs: Any ChannelInfo field (channel_name, creator_name, etc.)

    Example:
        setup_channel_programmatic(
            channel_name="TechSecurityPro",
            creator_name="John Doe",
            target_audience="cybersecurity professionals",
            content_style="educational",
            expertise_areas=["cybersecurity", "penetration testing", "AI security"]
        )
    """
    # Get current channel info or create new one
    current_info = config.channel_info or ChannelInfo()

    # Update fields
    for field, value in kwargs.items():
        if hasattr(current_info, field):
            setattr(current_info, field, value)
        else:
            print(f"Warning: Unknown field '{field}' ignored")

    config.channel_info = current_info
    print("✅ Channel information updated programmatically!")
    return current_info


def print_channel_summary(channel_info: ChannelInfo = None):
    """Print a summary of current channel configuration"""
    if channel_info is None:
        channel_info = config.channel_info

    print("\n📋 CURRENT CHANNEL CONFIGURATION")
    print("=" * 40)

    if channel_info.channel_name:
        print(f"📺 Channel: {channel_info.channel_name}")
    if channel_info.creator_name:
        print(f"👤 Creator: {channel_info.creator_name}")
    if channel_info.target_audience:
        print(f"🎯 Audience: {channel_info.target_audience}")
    if channel_info.content_style:
        print(f"🎨 Style: {channel_info.content_style}")
    if channel_info.expertise_areas:
        print(f"🧠 Expertise: {', '.join(channel_info.expertise_areas)}")
    if channel_info.unique_value_proposition:
        print(f"⭐ Unique Value: {channel_info.unique_value_proposition}")

    print()


def reset_channel_config():
    """Reset channel configuration to defaults"""
    config.channel_info = ChannelInfo()
    print("🔄 Channel configuration reset to defaults")


if __name__ == "__main__":
    # Run interactive setup when script is executed directly
    setup_channel_interactive()
