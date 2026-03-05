# Get Comments

## Endpoint

```
GET https://jsonplaceholder.typicode.com/comments
GET https://jsonplaceholder.typicode.com/comments/{id}
```

## Description

Returns comment data. Each comment includes the commenter's name, email, and the comment body. Comments are linked to posts via postId.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Optional. Comment ID (1-500) for a specific comment |
| postId | integer | Optional. Filter comments by post ID |

## Example Requests

```
GET https://jsonplaceholder.typicode.com/comments
GET https://jsonplaceholder.typicode.com/comments?postId=1
GET https://jsonplaceholder.typicode.com/posts/1/comments
```

## Example Response

```json
{
  "postId": 1,
  "id": 1,
  "name": "id labore ex et quam laborum",
  "email": "Eliseo@gardner.biz",
  "body": "laudantium enim quasi est quidem magnam voluptate..."
}
```

## Notes

- There are 500 comments in the dataset (IDs 1-500)
- Each post has exactly 5 comments
- Two ways to get comments for a post:
  - `GET /comments?postId=1` (query parameter)
  - `GET /posts/1/comments` (nested resource)
- Call dependency: use `get-posts` first to get valid postId values
