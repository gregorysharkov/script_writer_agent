from google.adk.agents import Agent, LoopAgent
from google.adk.tools import google_search

from ..config import config
from ..agent_utils import suppress_output_callback
from ..channel_utils import get_channel_aware_instruction

SCRIPT_WRITER_INSTRUCTION = """
You are a technical content writer for a youtube video.
Your job is to write a script for a youtube video.

The outline of the script is in the script_outline key from the context.

Your job is to write a script based on the outline.
Requirements:
1. Focus on developing the outline.
2. Split the script into sections based on the outline.
3. Focus on what should be said by the presenter. If necessary, place placeholders for visual aids.
4. The text should be concise and to the point.
5. The text should not sound like ai generated code, analogies, jokes, rythorical questions, etc. are welcome.

The script should be in markdown format.
"""

script_writer = Agent(
    model=config.main_model,
    name="script_writer",
    description="Agent to write a script for a youtube video.",
    instruction=get_channel_aware_instruction(
        SCRIPT_WRITER_INSTRUCTION, config.channel_info
    ),
    tools=[google_search],
    output_key="script",
    after_agent_callback=suppress_output_callback,
)

robust_script_writer = LoopAgent(
    name="robust_script_writer",
    description="A robust script writer that retries if it fails.",
    sub_agents=[script_writer],
    max_iterations=1,
    after_agent_callback=suppress_output_callback,
)
