---
name: docchat-author
description: Create or improve DocChat MCP knowledge packs from any API documentation source — OpenAPI specs, documentation URLs, or user descriptions. Handles the full workflow from information gathering to MCP server setup.
---

# DocChat Author

You are helping the user create a DocChat MCP knowledge pack. DocChat turns API documentation into an intelligent MCP server with deterministic routing (~80% of queries resolved without LLM calls).

## When to use this skill

- User wants to create a knowledge pack for an API
- User asks to "write docs for", "create knowledge files for", or "set up docchat for" an API
- User asks to "add a feed" or "improve" existing feed documentation
- User says the API has been "updated" or needs to "sync" the knowledge pack
- User mentions docchat, knowledge pack, or API documentation for MCP

## Workflow

### Phase 1: Gather API information

Collect **all available sources** before generating. Do NOT start writing after receiving just one source.

**Step 1: Accept the initial input** — whatever the user provides first:

1. **OpenAPI/Swagger spec file** (local `.json` or `.yaml`): Read it directly
2. **Spec URL** (e.g. `https://petstore.swagger.io/v2/swagger.json`): Fetch with WebFetch
3. **Documentation page URL**: Fetch the page, extract endpoint information (methods, paths, parameters, response fields)
4. **User description**: Ask the user to describe endpoints — method, path, parameters, response structure
5. **Existing knowledge pack with TODOs**: Read existing `feeds/*/META.yaml` and `feeds/*/GUIDE.md`, improve them

If the user provides nothing, ask: "Please provide an OpenAPI spec file, a documentation URL, or describe the API endpoints."

**Step 2: Ask for supplementary materials** — always ask before proceeding:

> I found N endpoints from [source]. Before I start generating, do you have any additional resources?
>
> - API documentation page URL?
> - Internal usage guides or wikis?
> - Common issues or gotchas to document?
> - Specific endpoints that need extra explanation?
>
> If not, I'll start generating based on what I have.

**Step 3: Fetch and merge** — if the user provides additional sources, read them all and merge the information. More sources = better keywords, descriptions, and FAQ content.

### Phase 2: Check for existing knowledge pack

Check if the current directory already has a knowledge pack:
- If `docchat.yaml` exists → this is an existing pack, add/improve feeds
- If `feeds/` exists with content → check what's already there, avoid duplicates
- If `docchat import` was already run → improve the skeleton (fill TODOs, add keywords)
- If nothing exists → create from scratch

**If the user is updating an existing pack**, determine the update scope first:

1. **User specifies what changed** (e.g. "the /pet endpoint has a new `weight` field"):
   - Update only the affected feed(s) directly — no need to re-read the entire spec
   - Add the new field to META.yaml `fields`, update GUIDE.md description and example

2. **User provides a new spec/URL** (e.g. "petstore.json has been updated"):
   - Read the new source and compare with existing feeds
   - Summarize the differences for the user:
     > I found the following changes:
     > - New endpoint: DELETE /pet/{petId}/tags
     > - Modified: POST /pet — added `weight` parameter
     > - Removed: GET /pet/findByColor
     >
     > Should I apply these changes?
   - Only modify feeds that have actual changes, leave the rest untouched

3. **User is unsure what changed** (e.g. "the API might have been updated"):
   - Ask: "Do you have the new spec file or documentation URL? I'll compare it with the current knowledge pack."
   - If no new source available, suggest: "You can check with the API provider for a changelog or updated spec."

### Phase 3: Generate knowledge pack

#### 3a. Create pack structure (if new)

```
my-api/
├── docchat.yaml
├── _overview/
│   └── INDEX.md
├── _shared/
│   ├── INDEX.yaml
│   └── error_codes.md
└── feeds/
    └── (one directory per endpoint or resource)
```

**docchat.yaml:**
```yaml
name: my-api                        # lowercase, no spaces
display_name: My API
version: 0.1.0
description: Brief API description
dimensions: []                      # empty for flat structure
assistant:
  name: API Assistant
  preamble_en: "You are an API technical support assistant. Answer based on the documentation below."
  preamble_zh: "你是 API 技术支持助手。请基于以下文档信息回答用户的问题。"
```

#### 3b. Create feeds

For each API endpoint, create `feeds/{feed-code}/` with:

**META.yaml** (most important — routing depends on this):

```yaml
name: get-users                     # Feed code = directory name
feed_name: Get Users                # Human-readable name
description: Returns a list of user profiles including name, email, and address.
endpoint: GET /api/users

triggers:
  keywords:
    # Comma-separated synonyms per line. English by default.
    - user list, get users, all users, list users, fetch users
    - user by id, specific user, single user
  scenarios:
    - Get a list of all users
    - Look up a specific user by ID

fields:
  - userId
  - userName
  - email
  - address
```

**GUIDE.md:**

```markdown
# Get Users

## Endpoint

`GET /api/users`

## Description

Returns a paginated list of user profiles. Each user includes basic info, contact details, and address.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Results per page (default: 20) |

## Example Response

\```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
\```

## Notes

- Requires authentication via Bearer token
- Rate limit: 100 requests/minute
```

#### 3c. Keyword generation strategy

This is the most critical part for routing quality. For each feed:

1. **From the summary/description**: extract key action + resource words
   - "Add a new pet to the store" → `add pet, create pet, new pet`
2. **From operationId**: split camelCase → `addPet` → `add pet`
3. **HTTP method synonyms**:
   - GET → `get, query, fetch, retrieve, list, 获取, 查询, 列表`
   - POST → `create, add, new, submit, 创建, 添加, 新建, 提交`
   - PUT → `update, modify, edit, change, 更新, 修改, 编辑`
   - DELETE → `delete, remove, 删除, 移除`
4. **Resource name variants**: singular/plural, abbreviations
   - `pet, pets, 宠物`
   - `order, orders, purchase, 订单, 购买`
5. **Other languages (optional)**: if the user's audience asks questions in non-English languages, add keyword lines in those languages too (e.g. Chinese: `用户列表, 获取用户, 查询用户`)
6. **Domain-specific terms**: add terms users would naturally use in context

Rules:
- Use commas to group synonyms on one line
- Avoid generic words alone: "data", "API", "get" — too broad
- Test mentally: "if someone types this keyword, should they land on THIS feed?"
- **Combine action + resource in multiple ways**: if the endpoint is "upload pet image", include `upload image, upload file, upload photo, pet image` — not just the exact summary wording. Users rarely type the exact phrase from the docs.

#### 3d. Create shared knowledge

**_shared/INDEX.yaml** — register cross-feed topics:

```yaml
topics:
  - path: error_codes.md
    keywords: [error, error code, status code, HTTP error, 错误码, 状态码]
  - path: auth/overview.md
    keywords: [authentication, auth, token, OAuth, API key, 认证, 鉴权, 授权]
```

**_shared/error_codes.md** — extract from spec's error responses:

```markdown
# Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request — invalid parameters |
| 401 | Unauthorized — missing or invalid auth |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource does not exist |
| 422 | Validation Error — request body invalid |
| 500 | Internal Server Error |
```

**_shared/auth/overview.md** — if the API has authentication:

```markdown
# Authentication

## Method

[OAuth 2.0 / API Key / Bearer Token — describe what the API uses]

## Usage

\```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.example.com/resource
\```
```

#### 3e. Create overview

**_overview/INDEX.md** — summarize the entire API:

```markdown
# API Name

Brief description of what this API does.

## Base URL

`https://api.example.com/v1`

## Authentication

[Brief auth description, refer to _shared/auth/overview.md for details]

## Available Feeds

| Feed | Endpoint | Description |
|------|----------|-------------|
| get-users | GET /users | List all users |
| create-user | POST /users | Create a new user |
```

### Phase 4: Validate

Run `docchat validate` to check the knowledge pack structure. Fix any warnings.

### Phase 5: Help user set up MCP server

Tell the user how to connect to their AI coding assistant:

```bash
# Install docchat-mcp (if not already installed)
pip install docchat-mcp

# Connect to Claude Code (run in the knowledge pack directory)
docchat connect

# Or from another directory:
docchat connect --dir /path/to/knowledge-pack/

# HTTP mode (for team sharing)
docchat serve --port 8710
```

## FAQ.md format (optional but recommended)

```markdown
# Feed Name FAQ

## Q: Why is the response empty?

**Check:** Verify your authentication token is valid and not expired.
**Cause:** Expired token, or the requested resource ID does not exist.
**Resolution:** Refresh your token. Verify the ID by calling the list endpoint first.
```

Rules:
- Every answer follows **Check → Cause → Resolution**
- Focus on real issues users encounter

## fields/ directory (optional, for complex responses)

For endpoints with deeply nested responses, split field docs:

```
fields/
├── root.md           # Top-level fields
├── address.md        # Nested address object
└── company.md        # Nested company object
```

Each file uses a table: `| Field | Type | Description |`

## Checklist before finishing

- [ ] `docchat.yaml` has name, display_name, assistant preambles
- [ ] Every feed has META.yaml with name, feed_name, description, endpoint
- [ ] Every feed has triggers.keywords in English (add other languages if needed)
- [ ] Every feed has fields list matching actual API response
- [ ] Every feed has GUIDE.md with endpoint, parameters, example response
- [ ] `_overview/INDEX.md` lists all feeds with descriptions
- [ ] `_shared/` has error codes and auth docs (if applicable)
- [ ] `docchat validate` passes with no warnings
