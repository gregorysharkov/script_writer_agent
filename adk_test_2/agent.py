"""ADK Test 2: Location Analyzer with Fan-out Pattern.

This module demonstrates the fan-out pattern in Google ADK where:
1. A LocationFinder agent searches for company locations and returns CIDs
2. A FanOutAgent dynamically creates LocationAnalyzer agents for each CID
3. Each LocationAnalyzer fetches images and performs LLM analysis
4. Results are stored in session state per location

Usage:
    from adk_test_2.agent import root_agent

    # Run with ADK
    adk run adk_test_2/

    # Or programmatically
    async with Session() as session:
        session.state["company_name"] = "acme_corp"
        async for event in root_agent.run_async(ctx):
            print(event)
"""

import logging
from functools import partial
from typing import AsyncGenerator

from google.adk.agents import SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from .agents.fan_out_agent import FanOutAgent
from .agents.location_finder import location_finder, LocationFinderSetup
from .agents.location_analyzer import create_location_analyzer

logger = logging.getLogger(__name__)


class CompanyInputSetup(BaseAgent):
    """Setup agent that initializes the company name from user input.

    This agent extracts the company name from the user's message
    and stores it in session state for downstream agents.
    """

    default_company: str = "acme_corp"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Extract company name and initialize session state.

        Args:
            ctx: The invocation context.

        Yields:
            Event indicating setup completion.
        """
        # Try to get company from user message or use default
        company_name = ctx.session.state.get("company_name", self.default_company)

        # Store in session state
        ctx.session.state["company_name"] = company_name

        logger.info(f"Initialized analysis for company: {company_name}")

        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(
                        text=f"Starting location analysis for: {company_name}"
                    )
                ]
            ),
        )


class ResultsAggregator(BaseAgent):
    """Agent that aggregates all analysis results into a summary.

    This agent runs after the fan-out completes and collects
    all individual analyses into a final summary.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Aggregate results from all location analyses.

        Args:
            ctx: The invocation context.

        Yields:
            Event with the aggregated summary.
        """
        cids = ctx.session.state.get("cids", [])

        if not cids:
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part.from_text(text="No locations were analyzed.")]
                ),
            )
            return

        # Collect all analyses
        analyses = []
        for cid in cids:
            analysis_key = f"analysis_{cid}"
            analysis = ctx.session.state.get(analysis_key)
            if analysis:
                analyses.append(analysis)

        # Store aggregated results
        ctx.session.state["all_analyses"] = analyses
        ctx.session.state["analysis_count"] = len(analyses)

        # Generate summary
        summary_parts = [
            f"## Location Analysis Complete\n",
            f"**Total Locations Analyzed:** {len(analyses)}\n",
        ]

        for i, analysis in enumerate(analyses, 1):
            assessment = analysis.get('overall_assessment', 'N/A')
            truncated = assessment[:200]
            ellipsis = "..." if len(assessment) > 200 else ""
            summary_parts.append(
                f"\n### {i}. {analysis.get('location_name', 'Unknown')}\n"
                f"- **Address:** {analysis.get('address', 'N/A')}\n"
                f"- **Type:** {analysis.get('place_type', 'N/A')}\n"
                f"- **Confidence:** {analysis.get('confidence_score', 0):.0%}\n"
                f"- **Assessment:** {truncated}{ellipsis}\n"
            )

        summary = "".join(summary_parts)

        logger.info(f"Aggregated {len(analyses)} location analyses")

        yield Event(
            author=self.name,
            content=Content(parts=[Part.from_text(text=summary)]),
        )


def on_agent_complete(callback_context: CallbackContext, agent_name: str):
    """Callback function triggered when an agent completes.

    Args:
        callback_context: The callback context.
        agent_name: Name of the agent that completed.
    """
    logger.info(f"Agent completed: {agent_name}")


# Create the setup agent
setup_agent = CompanyInputSetup(
    name="company_setup",
)

# Create the fan-out agent that processes each CID
location_fanout = FanOutAgent(
    name="location_fanout",
    items_key="cids",  # Session state key containing list of CIDs
    agent_factory=create_location_analyzer,  # Factory to create analyzer per CID
    description="Dynamically creates and runs analyzers for each location",
)

# Create the results aggregator
results_aggregator = ResultsAggregator(
    name="results_aggregator",
    description="Aggregates all location analyses into a final summary",
)

# Create the root sequential agent that orchestrates the entire pipeline
root_agent = SequentialAgent(
    name="location_analysis_pipeline",
    description=(
        "Complete location analysis pipeline: "
        "1) Setup company name, "
        "2) Find locations, "
        "3) Analyze each location in parallel, "
        "4) Aggregate results"
    ),
    sub_agents=[
        setup_agent,
        location_finder,
        location_fanout,
        results_aggregator,
    ],
    after_agent_callback=partial(on_agent_complete, agent_name="location_analysis_pipeline"),
)


# Export for ADK
__all__ = ["root_agent"]
