# DocChat MCP

> Turn your API docs into an intelligent MCP server with deterministic routing and layered knowledge injection.

[![PyPI version](https://img.shields.io/pypi/v/docchat-mcp)](https://pypi.org/project/docchat-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DocChat** transforms your API documentation into a smart [MCP](https://modelcontextprotocol.io/) server. AI assistants like Claude Code can query your API docs through natural language — with **~80% of queries resolved via deterministic routing** (zero LLM cost).

## How It Works

```
User question → Deterministic routing (trigger keywords / field names / feed codes)
                   ↓ matched                    ↓ not matched
           Load knowledge files          Return "needs LLM fallback"
                   ↓
    AI client receives structured docs and generates answer
```

The engine handles **routing + knowledge retrieval**. The AI client (Claude Code, Claude Desktop, etc.) handles **reasoning**.

## Features

- **Deterministic routing** — trigger keywords, field names, and feed codes match queries without LLM
- **Layered knowledge injection** — feed-level, overview, shared, and topic-matched knowledge
- **Custom dimensions** — organize feeds by any hierarchy (product, version, region, etc.)
- **MCP native** — 4 tools, 3 resources, 2 prompts — works with any MCP client
- **Zero LLM dependency** — the engine only provides data; AI reasoning is done by the client
- **CLI tooling** — `init` / `build` / `validate` / `serve` / `mcp`

## Quick Start

```bash
# Install
pip install docchat-mcp

# Initialize a knowledge pack
docchat init --name my-api

# Write your docs (see docs/writing-guide.md or use docchat-author skill)
# Each feed gets: META.yaml (triggers + fields) + GUIDE.md (usage guide)

# Validate format
docchat validate

# Build index
docchat build

# Start MCP server
docchat mcp        # stdio mode (for Claude Code)
docchat serve      # HTTP mode (for remote access)
```

## Connect to Claude Code

```bash
# Add as MCP server (stdio)
claude mcp add my-api -- docchat mcp --dir ./my-api-docs/

# Or via uvx (zero install)
claude mcp add my-api -- uvx docchat-mcp mcp --dir ./my-api-docs/
```

## Knowledge Pack Structure

```
my-api/
├── docchat.yaml          # Pack config (name, dimensions, assistant)
├── _shared/              # Shared knowledge (error codes, auth, etc.)
│   ├── INDEX.yaml        # Topic keywords for matching
│   └── error_codes.md
├── _overview/            # API overview
│   └── INDEX.md
└── feeds/                # One directory per API endpoint
    ├── get-users/
    │   ├── META.yaml     # Triggers, fields, description
    │   ├── GUIDE.md      # Usage guide
    │   ├── FAQ.md        # Optional: troubleshooting
    │   └── fields/       # Optional: field reference
    └── get-posts/
        ├── META.yaml
        └── GUIDE.md
```

See [docs/knowledge-pack-format.md](docs/knowledge-pack-format.md) for the full specification.

## Custom Dimensions

Organize feeds by any hierarchy via `docchat.yaml`:

```yaml
# Simple API (all feeds flat)
dimensions: []

# Two dimensions (product x sport)
dimensions:
  - key: product
    values: { rest: "REST API", ws: "WebSocket" }
  - key: sport
    values: { soccer: "Soccer", basketball: "Basketball" }
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_feeds` | List all available feeds |
| `search_by_field` | Find feeds by field name |
| `get_feed_info` | Get feed details + documentation |
| `route_question` | Route a query and return matched feeds + knowledge |

## Why Not RAG?

| Approach | Limitation | DocChat |
|----------|-----------|---------|
| Swagger UI | Browse only, no Q&A | Natural language queries |
| ChatGPT + docs | Full context dump, token overflow | Layered injection |
| RAG (embeddings) | Embedding quality varies, routing opaque | Deterministic routing (~80% zero LLM) |
| No MCP | AI can't access docs | MCP native, Claude Code direct |

## Demo

See it in action at [docchat.site](https://docchat.site)

## License

MIT
