"""Fan-out agent for dynamic parallel execution based on runtime data.

This module implements the core fan-out pattern where sub-agents are created
dynamically at runtime based on data in session state.
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

logger = logging.getLogger(__name__)


async def merge_async_generators(
    *generators: AsyncGenerator[Event, None],
) -> AsyncGenerator[Event, None]:
    """Merge multiple async generators into a single stream.

    This function runs all generators concurrently and yields events
    as they become available from any generator.

    Args:
        *generators: Variable number of async generators to merge.

    Yields:
        Events from all generators as they become available.
    """
    # Create tasks for each generator
    pending: set[asyncio.Task] = set()
    generator_map: dict[asyncio.Task, AsyncGenerator[Event, None]] = {}

    async def get_next(gen: AsyncGenerator[Event, None]) -> tuple[Event | None, bool]:
        """Get next item from generator, return (item, is_done)."""
        try:
            item = await anext(gen)
            return (item, False)
        except StopAsyncIteration:
            return (None, True)

    # Initialize tasks for all generators
    for gen in generators:
        task = asyncio.create_task(get_next(gen))
        pending.add(task)
        generator_map[task] = gen

    # Process until all generators are exhausted
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            gen = generator_map.pop(task)
            result, is_done = task.result()

            if not is_done and result is not None:
                yield result
                # Schedule next item from this generator
                new_task = asyncio.create_task(get_next(gen))
                pending.add(new_task)
                generator_map[new_task] = gen


class FanOutAgent(BaseAgent):
    """Agent that dynamically creates and runs sub-agents based on runtime data.

    This agent implements a fan-out pattern where:
    1. It reads a list of items from session state
    2. Creates a sub-agent for each item using a factory function
    3. Runs all sub-agents in parallel
    4. Collects and yields all events from the sub-agents

    Attributes:
        items_key: Session state key containing the list of items to process.
        agent_factory: Callable that creates an agent for each item.
        result_key_template: Template for storing results in session state.
    """

    items_key: str = ""
    agent_factory: Callable[[Any], BaseAgent] | None = None
    result_key_template: str = "analysis_{item}"

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Execute the fan-out pattern.

        Creates sub-agents for each item in the list and runs them in parallel.

        Args:
            ctx: The invocation context containing session state.

        Yields:
            Events from all sub-agents as they complete.
        """
        # Get the list of items from session state
        items = ctx.session.state.get(self.items_key, [])

        if not items:
            logger.warning(f"No items found in session state key '{self.items_key}'")
            yield Event(
                author=self.name,
                content=Content(
                    parts=[
                        Part.from_text(
                            text=f"No items to process (key: {self.items_key})"
                        )
                    ]
                ),
            )
            return

        logger.info(f"FanOutAgent '{self.name}' processing {len(items)} items: {items}")

        # Emit start event
        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(
                        text=f"Starting parallel analysis of {len(items)} locations"
                    )
                ]
            ),
        )

        # Create sub-agents dynamically
        sub_agents: list[BaseAgent] = []
        for item in items:
            try:
                agent = self.agent_factory(item)
                sub_agents.append(agent)
                logger.info(f"Created sub-agent '{agent.name}' for item: {item}")
            except Exception as e:
                logger.error(f"Failed to create agent for item {item}: {e}")
                yield Event(
                    author=self.name,
                    content=Content(
                        parts=[
                            Part.from_text(text=f"Error creating agent for {item}: {e}")
                        ]
                    ),
                )

        if not sub_agents:
            yield Event(
                author=self.name,
                content=Content(
                    parts=[Part.from_text(text="No sub-agents were created")]
                ),
            )
            return

        # Run all sub-agents in parallel
        logger.info(f"Running {len(sub_agents)} sub-agents in parallel")

        # Create async generators for each sub-agent
        generators = [agent._run_async_impl(ctx) for agent in sub_agents]

        # Merge and yield events from all generators
        async for event in merge_async_generators(*generators):
            yield event

        # Emit completion event
        yield Event(
            author=self.name,
            content=Content(
                parts=[
                    Part.from_text(
                        text=f"Completed parallel analysis of {len(items)} locations"
                    )
                ]
            ),
        )
