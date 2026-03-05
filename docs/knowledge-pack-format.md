# Knowledge Pack Format

A knowledge pack is a directory containing structured API documentation that DocChat can index and serve via MCP.

## docchat.yaml

The root configuration file. Required fields:

```yaml
name: my-api                    # Pack identifier (required)
display_name: "My API"          # Human-readable name
version: 1.0.0
description: "My API documentation"

dimensions: []                  # Classification hierarchy (see below)

assistant:
  name: "My API Assistant"
  preamble_en: "You are an assistant for My API..."
  preamble_zh: "你是 My API 的技术支持助手..."
```

### Dimensions

Dimensions let you organize feeds into a multi-level hierarchy. The engine generates composite index keys from dimension values.

- **Zero dimensions**: all feeds in `feeds/` directory
- **One dimension**: feeds in `{value}/` directories
- **Two dimensions**: feeds in `{value1}/{value2}/` directories

## Feed Directory

Each feed (API endpoint) is a directory containing:

| File | Required | Description |
|------|----------|-------------|
| `META.yaml` | Yes | Feed metadata, trigger keywords, field list |
| `GUIDE.md` | Recommended | Usage guide |
| `FAQ.md` | Optional | Troubleshooting (Check / Cause / Resolution) |
| `fields/*.md` | Optional | Field reference (one file per response level) |

### META.yaml

```yaml
name: get-users                     # Feed code (unique identifier)
feed_name: Get Users                # Human-readable name
description: Returns a list of users
endpoint: GET /api/users

triggers:
  keywords:
    - user list, get users          # Comma-separated synonyms
    - 用户列表, 获取用户            # Multi-language support
  scenarios:                        # Usage scenarios
    - Get a list of all users
    - Look up a specific user

fields:                             # Response field names
  - userId
  - userName
  - email
```

**Trigger keywords** are the core of deterministic routing. The engine matches user queries against these keywords without any LLM call. Tips:

- Include both English and Chinese keywords
- Use commas to separate synonyms on one line
- Add common misspellings and abbreviations
- Think about how users actually ask questions

### GUIDE.md

Standard format:

```markdown
# Feed Name

## Endpoint
## Description
## Parameters
## Example Request
## Example Response
## Notes
```

### FAQ.md

Use the Check / Cause / Resolution structure:

```markdown
# FAQ

## Q: Why is the response empty?

**Check:** Verify your auth token is valid.
**Cause:** Expired or invalid authentication token.
**Resolution:** Refresh your token and retry.
```

## _shared/ Directory

Shared knowledge files available across all feeds. Managed via `INDEX.yaml`:

```yaml
topics:
  - path: auth/overview.md
    keywords: [authentication, auth, token, OAuth]
  - path: error_codes.md
    keywords: [error, error code, status code]
    product: rest    # Optional: only load for this dimension value
```

The engine matches user message keywords against topic keywords and loads the relevant file.

## _overview/ Directory

API-level overview documents:

- `INDEX.md` — API overview, feed listing, getting started
- `COVERAGE_TIERS.md` — Optional: coverage tiers or data availability
