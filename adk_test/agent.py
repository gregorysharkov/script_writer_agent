import logging
import random
from functools import partial
from typing import AsyncGenerator, Any
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part

logger = logging.getLogger(__name__)

PIPELINE_TYPES = {
    "synonim_generator": {
        "prompt": "you are a synonym generator. You have to return a list of synonyms for a given word: {word}",
        "output_key": "synonyms",
    },
    "antonym_generator": {
        "prompt": "you are an antonym generator. You have to return a list of antonyms for a given word: {word}",
        "output_key": "antonyms",
    },
}

OUTPUT_FORMATS = {
    "text": "Just return the text of the response.",
    "json": "You have to return a list of synonyms for a given word: {word}. Return the response in JSON format.",
}


def add_custom_message(callback_context: CallbackContext, message: str):
    """callback function to add a custom message to the response."""
    logger.info(f"Adding custom message: {message}")


class AgentPipeline:
    """Sequential agent that returns a antonym, given a user input, given a user prompt."""

    def __init__(
        self,
        config: dict[str, dict[str, Any]],
        output_formats: dict[str, str],
    ):
        self.config = config
        self.output_formats = output_formats

    def create_pipeline(
        self, pipeline_type: str, output_key: str, return_type: str
    ) -> SequentialAgent:
        """Create a pipeline of agents that returns a antonym, given a user input, given a user prompt."""

        pipeline_type_config = self.config.get(pipeline_type, {})
        if not pipeline_type_config:
            raise ValueError(f"Pipeline type {pipeline_type} not found in config.")

        answer_generation_agent = LlmAgent(
            name=f"{pipeline_type}_answer_generator",
            model="gemini-2.5-flash",
            instruction=pipeline_type_config.get("prompt", ""),
            output_key=f"{output_key}_response",
        )

        output_format = self.output_formats.get(return_type, "")
        if not output_format:
            raise ValueError(f"Output format {return_type} not found in config.")

        formatting_agent = LlmAgent(
            name=f"{pipeline_type}_formatter",
            model="gemini-2.5-flash",
            instruction=output_format,
            output_key=f"{output_key}_formatted_response",
        )

        return SequentialAgent(
            name=f"{pipeline_type}_pipeline",
            description=f"Pipeline that returns a {output_key} for a given word.",
            sub_agents=[answer_generation_agent, formatting_agent],
        )


agent_list = [
    AgentPipeline(config=PIPELINE_TYPES, output_formats=OUTPUT_FORMATS).create_pipeline(
        pipeline_type=key,
        output_key=value["output_key"],
        return_type="text",
    )
    for key, value in PIPELINE_TYPES.items()
]

pipeline_agent = ParallelAgent(
    name="pipeline_agent",
    description="Parallel agent that runs the pipeline.",
    sub_agents=agent_list,
    after_agent_callback=partial(add_custom_message, message="Pipeline agent message"),
)


class InstructionSetter(BaseAgent):
    """Agent that sets the instruction for the pipeline."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        ctx.session.state["word"] = "beautiful"
        ctx.session.state["random_number"] = random.randint(1, 100)
        yield Event(
            author=self.name,
            content=Content(parts=[Part.from_text(text="Instruction set")]),
        )


def root_agent_callback(callback_context: CallbackContext):
    """Combined callback for root agent."""
    add_custom_message(callback_context, message="Root agent message")
    add_custom_message(callback_context, message="Pipeline agent message")


root_agent = SequentialAgent(
    name="root_agent",
    description="Root agent that sets the instruction for the pipeline.",
    sub_agents=[InstructionSetter(name="instruction_setter"), pipeline_agent],
    after_agent_callback=root_agent_callback,
)
