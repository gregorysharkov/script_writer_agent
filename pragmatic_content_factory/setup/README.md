# Knowledge Graph Setup Module

This module seeds the Neo4j knowledge graph with entities and relationships extracted from content sources defined in `worldview.md`.

## Overview

The setup pipeline:

1. **Parses** `worldview.md` to extract URLs and metadata
2. **Fetches** content based on URL type (web pages, PDFs, YouTube videos)
3. **Translates** non-English content to English using Gemini
4. **Extracts** entities and relationships using Gemini LLM
5. **Loads** structured data into Neo4j

```
worldview.md → Fetch Content → Translate → Extract Entities → Neo4j
                    ↓
              data/downloaded/
```

## Prerequisites

1. **Neo4j** running via Docker:
   ```bash
   cd pragmatic_content_factory
   docker-compose up -d
   ```

2. **Configuration** - Neo4j settings are loaded from:
   - `conf/neo4j_config.yaml` - connection URI, user, query settings
   - Environment variables override config file values

   Create `.env` at project root (copy from `env.example`):
   ```bash
   GOOGLE_API_KEY=your-google-api-key
   NEO4J_PASSWORD=password  # Password should be in .env, not config file
   
   # Optional overrides (defaults come from conf/neo4j_config.yaml):
   # NEO4J_URI=bolt://localhost:7687
   # NEO4J_USER=neo4j
   ```

3. **Dependencies** installed:
   ```bash
   pip install -r pragmatic_content_factory/requirements.txt
   ```

## Usage

### Run the seeding script

```bash
python -m pragmatic_content_factory.setup.seed_knowledge_graph
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--force`, `-f` | Reprocess all URLs even if previously processed |
| `--skip-fetch` | Skip fetching, use only previously downloaded content |
| `--worldview`, `-w` | Custom path to worldview.md file |

### Examples

```bash
# Normal run (skips already processed URLs)
python -m pragmatic_content_factory.setup.seed_knowledge_graph

# Force reprocess everything
python -m pragmatic_content_factory.setup.seed_knowledge_graph --force

# Use custom worldview file
python -m pragmatic_content_factory.setup.seed_knowledge_graph -w /path/to/custom.md
```

## Module Structure

```
setup/
├── __init__.py
├── seed_knowledge_graph.py     # Main entry point
├── parsers/
│   └── worldview_parser.py     # Parses worldview.md, extracts URLs
├── fetchers/
│   ├── web_fetcher.py          # Fetches web page content (httpx + BeautifulSoup)
│   ├── pdf_fetcher.py          # Downloads PDFs, extracts text (pypdf)
│   └── youtube_fetcher.py      # Processes YouTube via Gemini video understanding
├── processors/
│   ├── translator.py           # Language detection and translation (Gemini)
│   └── entity_extractor.py     # Entity/relationship extraction (Gemini)
└── loaders/
    └── neo4j_loader.py         # Neo4j persistence with MERGE queries
```

## Worldview File Format

The `data/seed/worldview.md` file defines source content:

```markdown
## EBooks
- https://example.com/article | title: Article Title

## Videos & Podcasts
- https://youtu.be/VIDEO_ID | title: "Video Title"

## Technical Writing
- https://example.com/doc.pdf | category: engineering
```

### Supported URL Types

| Type | Detection | Processing |
|------|-----------|------------|
| **Webpage** | Default | Fetch HTML, extract text with BeautifulSoup |
| **PDF** | URL ends with `.pdf` | Download to `data/downloaded/`, extract text |
| **YouTube** | Contains `youtube.com` or `youtu.be` | Gemini video understanding (transcription + summary) |

## Extracted Data

### Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| `Tool` | Technologies, frameworks, libraries | Docker, Kubernetes, Python |
| `Concept` | Ideas, principles, methodologies | MLOps, Clean Code, Latency |
| `Problem` | Pain points, challenges | Debugging Nightmare, Vendor Lock-in |
| `Person` | Brand persona (predefined) | Grigory |

### Relationship Types

| Type | Description |
|------|-------------|
| `HATES` | Strong negative sentiment |
| `PREFERS` | Positive sentiment, recommendations |
| `SKEPTICAL_OF` | Cautious stance |
| `VALUES` | Core beliefs, principles |
| `CAUSES` | Causal relationship (X causes Y) |
| `ENABLES` | Enabling relationship (X enables Y) |
| `SOLVES` | Solution relationship (X solves Y) |

## Exploring the Graph

### Neo4j Browser

Open http://localhost:7474 and login with your credentials.

### Useful Cypher Queries

**View all nodes and relationships:**
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

**Count entities by type:**
```cypher
MATCH (n) RETURN labels(n) as type, count(*) as count
```

**See Grigory's stances:**
```cypher
MATCH (p:Person {name: "Grigory"})-[r]->(t)
RETURN type(r) as stance, t.name as entity, r.reason
```

**Find all Tools:**
```cypher
MATCH (t:Tool) RETURN t.name, t.description
```

**See causal relationships:**
```cypher
MATCH (a)-[r:CAUSES|ENABLES|SOLVES]->(b)
RETURN a.name, type(r), b.name
```

## Data Persistence

- **Downloaded content**: `data/downloaded/` (PDFs saved here)
- **Processed URLs**: `data/downloaded/.processed.json` (tracks what's been processed)
- **Neo4j data**: `data/neo4j_data/` (Docker volume)

## Idempotency

- URLs are only marked as processed after successful graph update
- Use `MERGE` queries to avoid duplicates in Neo4j
- Re-running without `--force` skips already processed URLs
- Use `--force` to reprocess everything

## Troubleshooting

### "No new links to process"

All URLs have been processed. Use `--force` to reprocess:
```bash
python -m pragmatic_content_factory.setup.seed_knowledge_graph --force
```

Or delete the tracking file:
```bash
rm pragmatic_content_factory/data/downloaded/.processed.json
```

### "GOOGLE_API_KEY not set"

Ensure `.env` file exists at project root with:
```
GOOGLE_API_KEY=your-api-key
```

### Neo4j connection failed

1. Ensure Neo4j is running:
   ```bash
   docker-compose up -d
   docker-compose logs neo4j
   ```

2. Verify configuration in `conf/neo4j_config.yaml`:
   ```yaml
   connection:
     uri: "bolt://localhost:7687"
     user: "neo4j"
   ```

3. Ensure `NEO4J_PASSWORD` is set in `.env` file.
