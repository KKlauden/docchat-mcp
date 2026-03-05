# Knowledge File Writing Guide

This guide explains how to write effective knowledge files for DocChat. Well-written knowledge files enable accurate deterministic routing and high-quality AI responses.

## META.yaml

### Triggers

Triggers are the most important part — they determine whether a user's question gets routed to your feed.

**Keywords**

```yaml
triggers:
  keywords:
    - user list, get users, all users, list users
    - 用户列表, 获取用户, 查询用户
    - user profile, user info, user details
```

Guidelines:
- **Think like a user**: what words would someone use to ask about this endpoint?
- **Include synonyms**: "get users", "list users", "fetch users", "query users"
- **Include Chinese equivalents** if your users speak Chinese
- **Use commas** to separate synonyms on one line
- **Avoid overly generic keywords** like "data" or "API" that match everything
- **Test your triggers** with `docchat build` — the engine shows what gets indexed

**Scenarios**

```yaml
triggers:
  scenarios:
    - Get a list of all users
    - Look up a specific user by ID
    - Find user contact information
```

Scenarios are not used for routing but provide context for the AI assistant.

### Fields

List the response field names. These enable field-name routing — when a user asks "what is userId", the engine can route to the right feed.

```yaml
fields:
  - userId
  - userName
  - email
  - address
```

Use the exact field names from your API response.

## GUIDE.md

The main usage documentation. Recommended structure:

```markdown
# Feed Name

## Endpoint

GET /api/users
GET /api/users/{id}

## Description

One paragraph explaining what this endpoint does.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | No | User ID |

## Example Request

GET /api/users/1

## Example Response

{
  "id": 1,
  "name": "John Doe"
}

## Notes

- Important caveats or tips
- Rate limits
- Related endpoints
```

Guidelines:
- **Be factual**: describe what the API actually does, not what you think it should do
- **Include real examples**: actual request/response pairs help the AI give accurate answers
- **Note dependencies**: if this endpoint requires IDs from another endpoint, mention it
- **Keep it concise**: 200-500 words is usually enough

## FAQ.md

Use the Check / Cause / Resolution structure for each question:

```markdown
# FAQ

## Q: Why is the response empty?

**Check:** Verify your authentication token is valid.
**Cause:** Expired or invalid token; or the requested resource does not exist.
**Resolution:** Refresh your token. Verify the ID parameter is valid by calling the list endpoint first.

## Q: Why do I get a 403 error?

**Check:** Verify your subscription includes this endpoint.
**Cause:** Your API key does not have access to this resource.
**Resolution:** Contact support to upgrade your subscription.
```

## fields/ Directory

For endpoints with complex response structures, split field documentation into separate files by response level:

```
fields/
├── root.md           # Top-level fields
├── address.md        # Nested address object
└── company.md        # Nested company object
```

Each file documents the fields at that level with types and descriptions.

## _shared/INDEX.yaml

Register shared topics that apply across multiple feeds:

```yaml
topics:
  - path: auth/overview.md
    keywords: [authentication, auth, token, OAuth, API key]
  - path: error_codes.md
    keywords: [error, error code, status code, HTTP error]
  - path: pagination.md
    keywords: [pagination, page, page size, offset, limit]
    product: rest    # Optional: only for this dimension value
```

## _overview/INDEX.md

Write a concise overview of your API:

- Total number of endpoints/feeds
- How feeds are organized
- Base URL and authentication method
- A table listing all feeds with one-line descriptions
