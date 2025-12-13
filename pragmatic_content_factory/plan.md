# Pragmatic Content Factory - Implementation Plan

## Overview

Design the folder structure and component architecture for the Pragmatic Content Factory using Google ADK for agents, Pinecone for RAG, and Neo4j for the Knowledge Graph.

## Directory Structure

```
pragmatic_content_factory/
├── __init__.py
├── agent.py                    # Root agent orchestrator
├── config.py                   # Configuration dataclasses
├── requirements.md             # Requirements specification
├── architecture.md             # Architecture diagram
├── plan.md                     # This file
├── target_solution_architecture.md
│
├── agents/                     # The Crew - 5 specialized agents
│   ├── __init__.py
│   ├── deep_analyst.py         # Agent 1: The Extractor
│   ├── voice_architect.py      # Agent 2: The Ghostwriter
│   ├── ruthless_critic.py      # Agent 3: The Quality Gate
│   ├── atomizer.py             # Agent 4: The Distributor
│   └── librarian.py            # Agent 5: Memory Manager
│
├── memory/                     # The Brain - memory layer components
│   ├── __init__.py
│   ├── rag/                    # RAG Constitutional Layer
│   │   ├── __init__.py
│   │   ├── pinecone_client.py  # Pinecone vector store client
│   │   ├── embeddings.py       # Embedding generation
│   │   ├── retriever.py        # Document retrieval logic
│   │   └── indexer.py          # Document indexing (for Librarian)
│   │
│   └── knowledge_graph/        # Knowledge Graph Worldview Layer
│       ├── __init__.py
│       ├── neo4j_client.py     # Neo4j connection and queries
│       ├── entities.py         # Node/Entity definitions
│       ├── relationships.py    # Edge/Relationship definitions
│       └── queries.py          # Cypher query templates
│
├── models/                     # Pydantic models for data structures
│   ├── __init__.py
│   ├── content_brief.py        # Content Brief structure (Analyst output)
│   ├── draft.py                # Draft Script structure
│   ├── critique.py             # Critic evaluation result
│   ├── social_posts.py         # Atomizer output formats
│   └── feedback.py             # User feedback structure
│
├── data/                       # Static and dynamic documents
│   ├── static/                 # Read-only brand DNA (immutable)
│   │   ├── brand_passport.pdf
│   │   ├── reader_card.pdf
│   │   └── speech_code.pdf
│   │
│   └── dynamic/                # Librarian-managed documents
│       ├── taboo_list.md
│       └── style_adjustments.md
│
└── tools/                      # Shared tools for agents
    ├── __init__.py
    ├── rag_tools.py            # RAG query/update tools
    └── kg_tools.py             # Knowledge graph query/update tools
```

## Implementation Todos

| ID | Task | Status |
|----|------|--------|
| setup-structure | Create folder structure and __init__.py files | Completed |
| config | Create config.py with Pinecone/Neo4j/model settings | Pending |
| models | Create Pydantic models (content_brief, draft, critique, social_posts, feedback) | Pending |
| pinecone-client | Implement Pinecone client with embeddings and retriever | Pending |
| neo4j-client | Implement Neo4j client with entities and relationships | Pending |
| agent-analyst | Implement Deep Analyst agent | Pending |
| agent-writer | Implement Voice Architect agent | Pending |
| agent-critic | Implement Ruthless Critic agent | Pending |
| agent-atomizer | Implement Atomizer agent | Pending |
| agent-librarian | Implement Librarian agent | Pending |
| root-agent | Create root agent orchestrator with pipeline logic | Pending |
| data-files | Create placeholder static/dynamic data files | Pending |

## Component Responsibilities

### 1. Root Agent (agent.py)
- Orchestrates the main pipeline: `Input` -> `Analyst` -> `Writer` <-> `Critic` -> `Atomizer`
- Manages the Writer/Critic feedback loop until approval
- Routes user feedback to Librarian for learning loop

### 2. Agents (The Crew)

| Agent | File | Key Dependencies |
|-------|------|------------------|
| Deep Analyst | `agents/deep_analyst.py` | KG (read worldview) |
| Voice Architect | `agents/voice_architect.py` | RAG (read style/tone) |
| Ruthless Critic | `agents/ruthless_critic.py` | RAG (check rules) |
| Atomizer | `agents/atomizer.py` | None (pure transformation) |
| Librarian | `agents/librarian.py` | RAG (write), KG (write) |

### 3. Memory Layer (The Brain)

**RAG Layer (Pinecone)**
- `pinecone_client.py`: Initialize Pinecone, manage index
- `embeddings.py`: Generate embeddings (OpenAI/Gemini embeddings)
- `retriever.py`: Semantic search for style rules, taboos
- `indexer.py`: Add/update documents (used by Librarian)

**Knowledge Graph (Neo4j)**
- `neo4j_client.py`: Connection pool, transaction management
- `entities.py`: Node types (Tool, Concept, Person, Problem)
- `relationships.py`: Edge types (causes, solves, hates, etc.)
- `queries.py`: Predefined Cypher queries for common operations
