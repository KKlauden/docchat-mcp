# JSONPlaceholder Error Codes

JSONPlaceholder returns standard HTTP status codes:

| Code | Description |
|------|-------------|
| 200  | OK — Request succeeded |
| 201  | Created — Resource created (POST) |
| 404  | Not Found — Resource does not exist |
| 500  | Internal Server Error |

Note: JSONPlaceholder always returns 200 for valid resource paths, even if the ID does not exist (returns empty object `{}`). A 404 only occurs for completely invalid paths.
