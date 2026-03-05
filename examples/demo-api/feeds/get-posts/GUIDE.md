# Get Posts

## Endpoint

```
GET https://jsonplaceholder.typicode.com/posts
GET https://jsonplaceholder.typicode.com/posts/{id}
```

## Description

Returns blog post data. Each post has a title, body text, and a userId linking to the author. Use query parameters to filter posts.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Optional. Post ID (1-100) for a specific post |
| userId | integer | Optional. Filter posts by author user ID |

## Example Requests

```
GET https://jsonplaceholder.typicode.com/posts
GET https://jsonplaceholder.typicode.com/posts/1
GET https://jsonplaceholder.typicode.com/posts?userId=1
```

## Example Response

```json
{
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae consequuntur..."
}
```

## Notes

- There are 100 posts in the dataset (IDs 1-100)
- Each post belongs to one of the 10 users
- Nested resource: `GET /posts/1/comments` returns comments on post 1
- Call dependency: use `get-users` first to get valid userId values
