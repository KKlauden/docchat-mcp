---
name: docchat-author
description: Write knowledge files for DocChat MCP knowledge packs. Use when creating or improving META.yaml, GUIDE.md, FAQ.md, or fields/ for API endpoint documentation.
---

# DocChat Author

You are helping the user write knowledge files for a DocChat MCP knowledge pack. Follow the formats below exactly.

## When to use this skill

- User asks to "write docs for" or "create knowledge files for" an API endpoint
- User asks to "add a feed" to their knowledge pack
- User asks to "improve" or "update" existing feed documentation

## Workflow

1. **Understand the endpoint**: Ask the user for the API docs, Swagger spec, or description
2. **Create the feed directory**: `feeds/{feed-code}/`
3. **Write META.yaml first** — this is the most important file (routing depends on it)
4. **Write GUIDE.md** — usage guide with examples
5. **Optionally write FAQ.md** — if the user has common issues to document
6. **Optionally write fields/*.md** — for complex response structures
7. **Run `docchat validate`** to verify

## META.yaml Format

```yaml
name: get-users                     # Feed code (directory name, unique)
feed_name: Get Users                # Human-readable name
description: Returns a list of user profiles including name, email, and address.
endpoint: GET /api/users

triggers:
  keywords:
    # Comma-separated synonyms per line. Include BOTH English and Chinese.
    # Think: "what words would a developer use to ask about this?"
    - user list, get users, all users, list users, fetch users
    - 用户列表, 获取用户, 查询用户, 用户信息
    - user by id, specific user, single user
    - 按ID查用户, 查询单个用户
  scenarios:
    - Get a list of all users
    - Look up a specific user by ID
    - Find user contact information

fields:                             # Exact field names from API response
  - userId
  - userName
  - email
  - address
```

### Trigger keyword rules

- **Be exhaustive**: include every way a developer might refer to this endpoint
- **Include Chinese**: 中文关键词对中文用户至关重要
- **Use commas** to group synonyms on one line
- **Avoid generic words** alone: "data", "API", "get" — too broad, causes false matches
- **Include abbreviations**: if the endpoint is "Match Analysis", add "MA", "match analysis", "赛事分析"
- **Test mentally**: "if someone types this keyword, should they land on THIS feed?"

### Fields rules

- Use the **exact field names** from the API JSON response
- Include nested field names if they're commonly asked about (e.g. `address.city`)
- Fields enable field-name routing: user asks "what is userId" → routes to this feed

## GUIDE.md Format

```markdown
# Feed Name

## Endpoint

```
GET https://api.example.com/users
GET https://api.example.com/users/{id}
```

## Description

One paragraph: what this endpoint does and when to use it.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | No | User ID for a specific user |
| status | string | No | Filter by status: "active", "inactive" |

## Example Request

```
GET https://api.example.com/users?status=active
```

## Example Response

```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

## Call Dependencies

<!-- Only include if this endpoint requires IDs from another endpoint -->
`get-teams` → teamId → `get-users`

## Notes

- Important caveats, rate limits, or tips
- Related endpoints
```

### GUIDE.md rules

- **Be factual**: describe what the API does, based on actual documentation
- **Real examples**: use realistic request/response pairs
- **Note dependencies**: if you need an ID from another endpoint, document the chain
- **Parameter accuracy**: required/optional status must match the source docs exactly
- **Concise**: 200-500 words is usually sufficient

## FAQ.md Format

```markdown
# Feed Name FAQ

## Q: Why is the response empty?

**Check:** Verify your authentication token is valid and not expired.
**Cause:** Expired token, or the requested resource ID does not exist.
**Resolution:** Refresh your token. Verify the ID by calling the list endpoint first.

## Q: Why do I get a 403 error?

**Check:** Verify your subscription tier includes this endpoint.
**Cause:** Your API key does not have access to this resource.
**Resolution:** Contact support to upgrade your subscription.
```

### FAQ rules

- Every answer follows **Check → Cause → Resolution**
- **Check**: what the user should verify first
- **Cause**: the most likely root cause
- **Resolution**: concrete steps to fix it
- Focus on **real issues** users encounter, not hypothetical ones

## fields/ Directory

For complex responses, split field docs by response level:

```
fields/
├── root.md           # Top-level fields
├── address.md        # Nested address object
└── company.md        # Nested company object
```

Each file:

```markdown
# Address Fields

| Field | Type | Description |
|-------|------|-------------|
| street | string | Street address |
| city | string | City name |
| zipcode | string | ZIP/postal code |
| geo | object | Geographic coordinates |
| geo.lat | string | Latitude |
| geo.lng | string | Longitude |
```

## _shared/INDEX.yaml

If the user needs to add a shared topic (cross-feed knowledge like auth, error codes):

```yaml
topics:
  - path: auth/overview.md          # Relative to _shared/
    keywords: [authentication, auth, token, OAuth, API key]
  - path: error_codes.md
    keywords: [error, error code, status code]
    product: rest                    # Optional: dimension filter
```

Then create the corresponding .md file in `_shared/`.

## Checklist before finishing

- [ ] META.yaml has `name`, `feed_name`, `description`, `endpoint`
- [ ] Triggers include both English and Chinese keywords
- [ ] Triggers include common synonyms and abbreviations
- [ ] Fields list matches actual API response field names
- [ ] GUIDE.md has endpoint, parameters, example request/response
- [ ] Parameter required/optional status matches source docs
- [ ] Run `docchat validate` to check format
