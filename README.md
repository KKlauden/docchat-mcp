# DocChat MCP

> Turn your API docs into an intelligent MCP server with deterministic routing and layered knowledge injection.

English | [中文](README.zh-CN.md)

[![PyPI version](https://img.shields.io/pypi/v/docchat-mcp)](https://pypi.org/project/docchat-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DocChat** transforms your API documentation into a smart [MCP](https://modelcontextprotocol.io/) server. AI coding assistants like Claude Code can query your API docs through natural language — with **~80% of queries resolved via deterministic routing** (zero LLM cost).

## Use Case

You're building an app that calls a third-party API. You want Claude Code to understand that API — parameters, response fields, error codes, best practices — so it can write correct integration code.

```
Your API docs → DocChat → MCP server (runs locally) → Claude Code queries it while coding
```

DocChat is the bridge: it turns your docs into structured knowledge that AI assistants can search and retrieve on demand.

## How It Works

```
                          Your machine
┌───────────────────────────────────────────────────┐
│                                                   │
│  Claude Code ◄── stdio ──► docchat mcp            │
│    (LLM)                    (local process)       │
│      │                         │                  │
│      │ "How do I call          │ reads from       │
│      │  the users API?"        ▼                  │
│      │                    ./my-api-docs/           │
│      │                    ├── META.yaml            │
│      │                    ├── GUIDE.md             │
│      ▼                    └── ...                  │
│  Generates answer                                 │
│  using retrieved docs                             │
│                                                   │
└───────────────────────────────────────────────────┘
```

The engine handles **routing + knowledge retrieval**. The AI client handles **reasoning**. No external services, no extra LLM calls.

## Quick Start

### 1. Install

```bash
pip install docchat-mcp
```

### 2. Create your knowledge pack

**Option A: Import from OpenAPI spec** (recommended)

```bash
docchat import your-api-spec.json
```

This parses your OpenAPI spec (JSON/YAML, v2.0/3.x) and generates feed skeletons automatically — META.yaml with fields + endpoint info, and GUIDE.md with parameters, response fields, and examples. You just need to add trigger keywords and refine the docs.

**Option B: Start from scratch**

```bash
docchat init --name my-api
```

Then manually create each feed directory:

```bash
my-api/
└── feeds/
    └── get-users/
        ├── META.yaml   # Trigger keywords + field names (for routing)
        └── GUIDE.md    # Usage guide (for answering)
```

See [docs/writing-guide.md](docs/writing-guide.md) for the format, or use the `docchat-author` skill to let Claude Code help you write them.

### 3. Validate and build

```bash
docchat validate    # Check format
docchat build       # Verify index loads correctly
```

### 4. Connect to Claude Code

```bash
# Register as a local MCP server (runs on your machine via stdio)
claude mcp add my-api -- docchat mcp --dir ./my-api-docs/

# Or via uvx (no prior install needed)
claude mcp add my-api -- uvx docchat-mcp mcp --dir ./my-api-docs/
```

That's it. Now when you ask Claude Code about your API, it queries DocChat's MCP server locally, retrieves the relevant docs, and generates accurate answers.

### Team sharing (optional)

If you want multiple people to use the same knowledge pack:

```bash
# Start HTTP server on a shared machine
docchat serve --port 8000

# Team members connect remotely
claude mcp add my-api --transport http http://your-server:8000/mcp/
```

## Features

- **Deterministic routing** — trigger keywords, field names, and feed codes match queries without LLM
- **Layered knowledge injection** — feed-level, overview, shared, and topic-matched knowledge
- **Custom dimensions** — organize feeds by any hierarchy (product, version, region, etc.)
- **MCP native** — 4 tools, 3 resources, 2 prompts — works with any MCP client
- **Zero LLM dependency** — the engine only provides data; AI reasoning is done by the client
- **OpenAPI import** — `docchat import spec.json` generates feed skeletons from OpenAPI specs (v2.0/3.x)
- **CLI tooling** — `init` / `import` / `build` / `validate` / `serve` / `mcp`

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

## Updating

**Knowledge files changed** (META.yaml, GUIDE.md, etc.): Restart Claude Code. The MCP server reloads on startup.

**Engine updated** (new docchat-mcp version):

```bash
pip install --upgrade docchat-mcp
# Then restart Claude Code

# If using uvx, clear cache first:
uv cache clean docchat-mcp
```

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
