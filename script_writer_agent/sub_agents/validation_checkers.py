from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai.types import Content


class OutlineValidationChecker(BaseAgent):
    """Checks if the script outline is valid."""

    async def _run_async_impl(
        self, context: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Only escalate if there's NO outline (error condition)
        if not context.session.state.get("script_outline"):
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
                content=Content(
                    parts=[
                        {
                            "text": "No script outline found. Please generate an outline first."
                        }
                    ]
                ),
            )
        # If outline exists, validation passed - don't yield anything
        # This tells the LoopAgent that the task is complete and it should stop retrying
