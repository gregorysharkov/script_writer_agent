"""Pragmatic Content Factory - Root Agent Pipeline.

This module defines the main agent pipeline using Google ADK's
SequentialAgent pattern for orchestrating the content generation flow.

Current Pipeline:
    Input → Deep Analyst → [Content Brief]

Future Pipeline:
    Input → Deep Analyst → [CP1] → Voice Architect → [CP2] →
    Ruthless Critic ↔ Writer → [CP3] → Atomizer → Output
"""

from dotenv import load_dotenv
from google.adk.agents import SequentialAgent

from pragmatic_content_factory.agents.deep_analyst import deep_analyst

load_dotenv()


# Pipeline instruction for the orchestrator
PIPELINE_INSTRUCTION = """You are the Pragmatic Content Factory pipeline orchestrator.

## Purpose

You coordinate the content generation pipeline, passing content through
specialized agents that each perform a specific task.

## Current Pipeline

1. **Deep Analyst** (The Extractor)
   - Receives: Raw input (transcripts, ideas, notes)
   - Produces: Structured Content Brief
   - Queries Knowledge Graph for worldview context

## How It Works

When you receive raw input:
1. Pass it to the Deep Analyst
2. The analyst will query the Knowledge Graph for relevant worldview context
3. The analyst produces a structured Content Brief
4. The Content Brief is stored in context as 'content_brief'

## Input Format

The input should contain:
- Raw text content (transcript, ideas, notes)
- Optional: Source type (transcript, notes, idea)
- Optional: Target content type (youtube_script, linkedin_post)

## Output

The pipeline currently produces a Content Brief containing:
- Key insight and its strength
- Audience pain points addressed
- Social currency angles
- Structured talking points
- Worldview context from Knowledge Graph
- Suggested angle and analyst notes

## Future Agents (Coming Soon)

- **Voice Architect**: Will take Content Brief and produce Draft Script
- **Ruthless Critic**: Will validate drafts against brand rules
- **Atomizer**: Will create platform-specific content from final script
- **Librarian**: Will manage memory updates from user feedback

## Human-in-the-Loop Checkpoints (Coming Soon)

- CP1: After Deep Analyst (Brief Review)
- CP2: After Voice Architect (Draft Review)  
- CP3: After Ruthless Critic (Final Review)

For now, the pipeline runs the Deep Analyst and returns the Content Brief.
"""


# Root agent using SequentialAgent pattern
# Currently only contains Deep Analyst, will be extended with other agents
root_agent = SequentialAgent(
    name="pragmatic_content_factory",
    description=(
        "Content generation pipeline for the Pragmatic Architect brand. "
        "Analyzes raw input and produces structured content briefs."
    ),
    sub_agents=[
        deep_analyst,
        # Future agents will be added here:
        # voice_architect,
        # ruthless_critic,
        # atomizer,
    ],
)
