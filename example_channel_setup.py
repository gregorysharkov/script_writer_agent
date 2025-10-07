#!/usr/bin/env python3
"""
Example: How to set up and use channel information with Script Writer Agent

This example demonstrates how to configure your channel information and use it
to generate personalized scripts.
"""

from script_writer_agent.setup_channel import (
    setup_channel_programmatic,
    setup_channel_interactive,
    print_channel_summary,
    reset_channel_config,
)
from script_writer_agent.config import config
from script_writer_agent.agent import root_agent


def example_programmatic_setup():
    """Example of setting up channel info programmatically"""
    print("🔧 EXAMPLE: Programmatic Channel Setup")
    print("=" * 50)

    # Set up channel information programmatically
    setup_channel_programmatic(
        channel_name="CyberSecurityMaster",
        creator_name="Alex Johnson",
        channel_description="Advanced cybersecurity tutorials and real-world scenarios",
        target_audience="cybersecurity professionals and ethical hackers",
        content_style="educational with practical demonstrations",
        tone_of_voice="authoritative but approachable",
        expertise_areas=[
            "penetration testing",
            "network security",
            "AI security",
            "incident response",
        ],
        unique_value_proposition="Real-world scenarios from 15+ years in cybersecurity",
        creator_background="Senior Security Consultant, CISSP certified, former red team lead",
        personal_story="Started as a developer, learned security the hard way through breaches",
        preferred_video_length="10-15 minutes",
        call_to_action_style="Ask viewers to share their own security experiences in comments",
        engagement_preferences="Respond to technical questions, encourage community discussion",
        visual_style_notes="Dark theme, terminal demos, network diagrams",
        production_constraints="Home office setup, limited to screen recordings and webcam",
    )

    # Show the configuration
    print_channel_summary()


def example_interactive_setup():
    """Example of interactive setup (commented out to avoid prompts in demo)"""
    print("🎮 EXAMPLE: Interactive Channel Setup")
    print("=" * 50)
    print("To run interactive setup, uncomment the line below:")
    print("# setup_channel_interactive()")
    print()

    # Uncomment this line to run interactive setup:
    # setup_channel_interactive()


def example_usage_with_agent():
    """Example of how channel info affects agent behavior"""
    print("🤖 EXAMPLE: How Channel Info Affects Agents")
    print("=" * 50)

    # First, let's see what happens with no channel info
    reset_channel_config()
    print("📝 Agent instruction WITHOUT channel info:")
    print("Length:", len(root_agent.instruction))
    print(
        "Contains 'CyberSecurityMaster':",
        "CyberSecurityMaster" in root_agent.instruction,
    )
    print()

    # Now set up channel info
    setup_channel_programmatic(
        channel_name="CyberSecurityMaster",
        creator_name="Alex Johnson",
        target_audience="cybersecurity professionals",
    )

    # Check how it affects the agents (need to recreate them to pick up new config)
    from script_writer_agent.sub_agents.script_panner import script_panner

    print("📝 Script Planner instruction WITH channel info:")
    print("Length:", len(script_panner.instruction))
    print(
        "Contains 'CyberSecurityMaster':",
        "CyberSecurityMaster" in script_panner.instruction,
    )
    print(
        "Contains 'cybersecurity professionals':",
        "cybersecurity professionals" in script_panner.instruction,
    )
    print()


def show_all_examples():
    """Run all examples"""
    print("🎬 Script Writer Agent - Channel Integration Examples")
    print("=" * 60)
    print()

    example_programmatic_setup()
    print()

    example_interactive_setup()
    print()

    example_usage_with_agent()
    print()

    print("✅ All examples completed!")
    print()
    print("💡 Next steps:")
    print("1. Set up your own channel info using setup_channel_interactive()")
    print("2. Use the root_agent to generate personalized scripts")
    print("3. All scripts will now incorporate your channel preferences!")


if __name__ == "__main__":
    show_all_examples()
