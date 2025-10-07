from google.adk.agents import Agent, LoopAgent
from google.adk.tools import google_search

from ..config import config
from ..agent_utils import suppress_output_callback
from ..channel_utils import get_channel_aware_instruction

SCRIPT_PANNER_INSTRUCTION = """
You are a technical content strategist. Your job is to create an outline for a script for a video.
The outline should well-structured and easy to follow.
it should include the following sections:
- Title
- Main message
- 3-5 key points/roadmap

Use Google Search to find relevant information and examples to support your work.
Your outline should be in markdown format.

The outline guidelines:
- Title options:
    - what is the worst <scenario/error/choice> for the <target audience>? And how to avoid it using <solution/tool/strategy>?
    - how to <task/skill> using <solution/tool/strategy>?
Example: What is the worst scnario for bank's anti-fraud system? And how to break it in 2025?

- Main message options:
    - hook. Show the worst <scenario/error/choice> for the <target audience>.
    - why should the <target audience> care about this?
    - why should the <target audience> trust me?

- Roadmap options:
    - 3-5 key points to cover the main message.
    - each key point should be a sub-heading in the outline.

Example:
- Title: What is the worst scenario for bank's anti-fraud system? And how to break it in 2025?
- Main message: Show the worst scenario for bank's anti-fraud system.

Solution options:
    - step 1. Quick win
    - step 2. Systematic solution
    - step 3. Overkill solution with extra contingency

Weaknesses and constraints:
    - what if the solution is not practical or achievable?
    - provide boundaries, where the solution is not applicable.
"""


script_panner = Agent(
    model=config.main_model,
    name="script_panner",
    description="Agent to plan a script for a video.",
    instruction=get_channel_aware_instruction(
        SCRIPT_PANNER_INSTRUCTION, config.channel_info
    ),
    tools=[google_search],
    output_key="script_outline",
    after_agent_callback=suppress_output_callback,
)

robust_script_panner = LoopAgent(
    name="robust_script_panner",
    description="A robust script planner that retries if it fails.",
    sub_agents=[script_panner],
    max_iterations=1,  # Only run once to avoid the 3-iteration issue
    after_agent_callback=suppress_output_callback,
)
