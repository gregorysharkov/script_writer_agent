"""Pragmatic Content Factory - Root Agent Pipeline.

This module defines the main agent pipeline using Google ADK's
SequentialAgent pattern for orchestrating the content generation flow.

Current Pipeline:
    Input → Deep Analyst → [Content Brief] → Librarian → [Memory Updates]

Future Pipeline:
    Input → Deep Analyst → [CP1] → Voice Architect → [CP2] →
    Ruthless Critic ↔ Writer → [CP3] → Atomizer → Output
    (with Librarian processing feedback at each checkpoint)
"""

from dotenv import load_dotenv
from google.adk.agents import SequentialAgent

from pragmatic_content_factory.agents.deep_analyst import deep_analyst
from pragmatic_content_factory.agents.librarian import librarian

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

2. **Librarian** (Memory Manager)
   - Receives: Content Brief and user feedback
   - Analyzes for learning signals (URLs, stances, taboo terms, style preferences)
   - Updates Knowledge Graph and RAG index as needed
   - Uses confidence-based actions: auto-stores HIGH, confirms MEDIUM

## How It Works

When you receive raw input:
1. Pass it to the Deep Analyst
2. The analyst will query the Knowledge Graph for relevant worldview context
3. The analyst produces a structured Content Brief
4. The Content Brief is stored in context as 'content_brief'
5. The Librarian analyzes the messages and user feedback for learning signals
6. The Librarian updates memory (KG/RAG) based on detected signals

## Input Format

The input should contain:
- Raw text content (transcript, ideas, notes)
- Optional: Source type (transcript, notes, idea)
- Optional: Target content type (youtube_script, linkedin_post)
- Optional: URLs to process into knowledge graph

## Output

The pipeline produces:

**From Deep Analyst:**
- Key insight and its strength
- Audience pain points addressed
- Social currency angles
- Structured talking points
- Worldview context from Knowledge Graph
- Suggested angle and analyst notes

**From Librarian:**
- Memory updates performed (entities, relationships, taboo terms, style adjustments)
- Pending confirmations for MEDIUM confidence items
- Summary of what was stored

## Librarian Learning Signals

The Librarian detects and processes:
- URLs mentioned → Extracts entities/relationships to Knowledge Graph
- Taboo terms → Adds to taboo list and RAG index
- Stances/opinions → Creates relationships in Knowledge Graph
- Style preferences → Records in style adjustments and RAG index

## Future Agents (Coming Soon)

- **Voice Architect**: Will take Content Brief and produce Draft Script
- **Ruthless Critic**: Will validate drafts against brand rules
- **Atomizer**: Will create platform-specific content from final script

## Human-in-the-Loop Checkpoints (Coming Soon)

- CP1: After Deep Analyst (Brief Review)
- CP2: After Voice Architect (Draft Review)  
- CP3: After Ruthless Critic (Final Review)

At each checkpoint, users can provide feedback that the Librarian will process.
"""


# Root agent using SequentialAgent pattern
root_agent = SequentialAgent(
    name="pragmatic_content_factory",
    description=(
        "Content generation pipeline for the Pragmatic Architect brand. "
        "Analyzes raw input, produces structured content briefs, and "
        "updates memory based on user feedback and content analysis."
    ),
    sub_agents=[
        deep_analyst,
        librarian,
        # Future agents will be added here:
        # voice_architect,
        # ruthless_critic,
        # atomizer,
    ],
)
