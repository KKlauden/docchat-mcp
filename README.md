# DocChat MCP

> Turn your API docs into an intelligent MCP server with deterministic routing and layered knowledge injection.

**DocChat** transforms your API documentation into a smart MCP (Model Context Protocol) server. AI assistants like Claude Code can query your API docs through natural language — with ~80% of queries resolved via deterministic routing (zero LLM cost).

## Features

- **Deterministic routing** — trigger keywords, field names, and feed codes match queries without LLM
- **Layered knowledge injection** — feed-level, overview, shared, and topic-matched knowledge
- **Custom dimensions** — organize feeds by any hierarchy (product, version, region, etc.)
- **MCP native** — works with Claude Code, Claude Desktop, and any MCP client
- **Zero LLM dependency** — the engine only provides data; AI reasoning is done by the client

## Quick Start

```bash
# Install
pip install docchat-mcp

# Initialize a knowledge pack
docchat init --name my-api

# Write your docs (or use docchat-author skill with Claude Code)
# ...

# Build index
docchat build

# Start MCP server (stdio mode for Claude Code)
docchat mcp

# Or HTTP mode for remote access
docchat serve
```

## Connect to Claude Code

```bash
claude mcp add my-api -- docchat mcp --dir ./my-api-docs/
```

## Demo

See it in action at [docchat.site](https://docchat.site)

## License

MIT
