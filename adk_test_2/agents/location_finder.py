"""Location finder agent that searches for company locations.

This agent uses (mock) Google Maps tools to find candidate locations
for a given company and stores the CIDs in session state for the
fan-out agent to process.
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import LlmAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from ..tools.maps_tools import find_locations

logger = logging.getLogger(__name__)


class LocationFinderSetup(BaseAgent):
    """Setup agent that extracts the company name from user input.

    This agent runs before the LLM agent to ensure the company name
    is available in session state for tool calls.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Extract company name from user message and store in state.

        Args:
            ctx: The invocation context.

        Yields:
            Event indicating setup completion.
        """
        # The company name should come from the user's initial message
        # For now, we'll set a default that can be overridden
        if "company_name" not in ctx.session.state:
            ctx.session.state["company_name"] = "acme_corp"
            logger.info("Set default company name: acme_corp")

        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(
                        text=f"Setup complete. Company: {ctx.session.state['company_name']}"
                    )
                ]
            ),
        )


class LocationFinderAgent(BaseAgent):
    """Agent that finds locations and stores CIDs in session state.

    This is a custom agent that:
    1. Calls the find_locations tool with the company name
    2. Extracts the CIDs from the result
    3. Stores both the full results and just the CIDs in session state
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Find locations for the company and store in session state.

        Args:
            ctx: The invocation context.

        Yields:
            Events describing the search progress and results.
        """
        company_name = ctx.session.state.get("company_name", "default")

        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(text=f"Searching for locations of: {company_name}")
                ]
            ),
        )

        # Call the mock tool
        try:
            result = find_locations(company_name)

            # Store results in session state
            ctx.session.state["location_search_result"] = result
            ctx.session.state["locations"] = result["locations"]
            ctx.session.state["cids"] = result["cids"]

            # Create a mapping of CID to location info for later use
            ctx.session.state["cid_to_location"] = {
                loc["cid"]: loc for loc in result["locations"]
            }

            logger.info(f"Found {len(result['cids'])} locations: {result['cids']}")

            yield Event(
                author=self.name,
                content=Content(
                    parts=[
                        Part.from_text(
                            text=f"Found {result['total_count']} locations:\n"
                            + "\n".join(
                                f"- {loc['name']} ({loc['cid']})"
                                for loc in result["locations"]
                            )
                        )
                    ]
                ),
            )

        except Exception as e:
            logger.error(f"Error finding locations: {e}")
            ctx.session.state["cids"] = []
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part.from_text(text=f"Error searching for locations: {e}")]
                ),
            )


# Create the location finder agent instance
location_finder = LocationFinderAgent(
    name="location_finder",
    description="Finds candidate locations for a company using Google Maps",
)


# Alternative: LLM-based location finder that uses tools
# This version allows the LLM to decide how to search
LOCATION_FINDER_INSTRUCTION = """You are a location research assistant. Your task is to find 
all relevant locations for a given company.

When given a company name, use the find_locations tool to search for their locations.
Report back the locations found, including their names, addresses, and CIDs.

The CIDs are important as they will be used to fetch imagery for analysis.
"""

llm_location_finder = LlmAgent(
    name="llm_location_finder",
    model="gemini-2.5-flash",
    instruction=LOCATION_FINDER_INSTRUCTION,
    tools=[find_locations],
    output_key="location_search_response",
    description="LLM-powered location finder using Google Maps tools",
)
