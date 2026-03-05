# Get Users

## Endpoint

```
GET https://jsonplaceholder.typicode.com/users
GET https://jsonplaceholder.typicode.com/users/{id}
```

## Description

Returns user profile data. Each user object includes personal info (name, email, phone), address (with geo coordinates), and company details.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Optional. User ID (1-10) for a specific user |

## Example Request

```
GET https://jsonplaceholder.typicode.com/users/1
```

## Example Response

```json
{
  "id": 1,
  "name": "Leanne Graham",
  "username": "Bret",
  "email": "Sincere@april.biz",
  "address": {
    "street": "Kulas Light",
    "suite": "Apt. 556",
    "city": "Gwenborough",
    "zipcode": "92998-3874",
    "geo": { "lat": "-37.3159", "lng": "81.1496" }
  },
  "phone": "1-770-736-8031 x56442",
  "website": "hildegard.org",
  "company": {
    "name": "Romaguera-Crona",
    "catchPhrase": "Multi-layered client-server neural-net",
    "bs": "harness real-time e-markets"
  }
}
```

## Notes

- There are exactly 10 users in the dataset (IDs 1-10)
- Nested resources: `GET /users/1/posts` returns posts by user 1
- Nested resources: `GET /users/1/todos` returns todos for user 1
