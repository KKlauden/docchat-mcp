---
name: docchat-reviewer
description: Audit a DocChat knowledge pack for content quality — keyword coverage, documentation completeness, and field consistency. Use when the user asks to review, audit, or check quality of a knowledge pack.
---

# DocChat Reviewer

You are auditing a DocChat MCP knowledge pack for content quality. This review complements `docchat validate` (which checks structural correctness) by examining **content quality** — things that require judgment rather than mechanical checks.

## When to use this skill

- User asks to "review", "audit", "check quality", or "evaluate" a knowledge pack
- User wants to improve routing accuracy or documentation completeness
- User asks "is my knowledge pack ready?" or "what should I improve?"

## Review Protocol

### Step 1: Structural pre-check

Run `docchat validate` first (or `docchat validate --dir <path>` if not in the pack directory). If there are structural errors, report them and ask the user to fix those before proceeding with the content review.

### Step 2: Inventory

Scan the knowledge pack and build an inventory:
- Read `docchat.yaml` for pack metadata
- List all feed directories under `feeds/` (or dimension-based paths)
- Check for `_overview/INDEX.md`, `_shared/INDEX.yaml`, and shared knowledge files
- Count total feeds and note which files each feed has (META.yaml, GUIDE.md, FAQ.md, fields/)

Present the inventory as a summary before diving into findings.

### Step 3: Apply checklist

For each feed, check the following. Classify every finding by severity:

**Error** (must fix — directly impacts routing or correctness):

- META.yaml has no `triggers.keywords` or the list is empty
- Keywords contain overly generic standalone terms that match everything: "data", "API", "get", "info", "request", "response"
- META.yaml has no `fields` list
- GUIDE.md does not exist
- `_overview/INDEX.md` does not exist
- `_shared/INDEX.yaml` references a file that does not exist

**Warning** (should fix — reduces quality):

- Keywords exist in only one language (if the pack targets multilingual users)
- Fewer than 3 keyword synonym groups (low recall — users asking in different ways won't match)
- Keywords lack action+resource combinations (e.g. only has "users" but not "get users", "list users", "fetch users")
- `fields` list does not match the JSON keys shown in GUIDE.md's Example Response
- GUIDE.md is missing a Parameters section or Example Response section
- FAQ.md exists but does not follow the Check / Cause / Resolution structure
- `_overview/INDEX.md` feed listing does not match actual feeds in `feeds/`
- `_shared/` has no error codes documentation

**Info** (consider improving):

- Fewer than 5 keyword synonym groups (could improve recall)
- No domain-specific or colloquial terms in keywords
- GUIDE.md is missing a Notes section
- FAQ.md does not exist (recommended for complex feeds with common pitfalls)
- No `fields/` directory (recommended for endpoints with deeply nested responses)
- `_shared/` has no authentication documentation

### Step 4: Produce report

Output a structured review with these sections:

```
## Knowledge Pack Review: {pack_name}

### Summary
- Total feeds: N
- Files scanned: N
- Overall quality: [brief assessment]

### Errors (N)
[grouped by issue type, each with feed name and specific problem]

### Warnings (N)
[grouped by issue type]

### Info (N)
[grouped by issue type]

### Score: X/10
[Brief justification based on error/warning counts and overall completeness]

### Top 3 Recommendations
1. [Most impactful improvement]
2. [Second most impactful]
3. [Third most impactful]
```

### Step 5: Guide next steps

End the report with:

> To fix the issues above, you can use `/docchat-author` and provide this review as context. The author skill can generate missing keywords, complete GUIDE.md sections, and create FAQ.md files.

## Keyword Quality Criteria

When evaluating trigger keywords, apply these standards:

1. **Coverage**: Keywords should include synonyms across phrasing styles
   - Good: `get users, list users, fetch users, query users, user list`
   - Bad: `get-users` (only the exact operation ID)

2. **Specificity**: Keywords should be specific enough to route to ONE feed
   - Good: `create pet, add new pet, register pet`
   - Bad: `data, create` (too broad, matches everything)

3. **Action + Resource**: Combine verbs with resource nouns
   - Good: `upload pet image, pet photo upload, add pet picture`
   - Bad: `upload, image, photo` (individual words match too broadly)

4. **Multilingual** (if applicable): Include terms in the languages your users speak
   - Example: `get users, list users, 获取用户, 用户列表, 查询用户`

5. **Domain terms**: Include terminology your users actually use
   - If users say "roster" instead of "user list", add it
