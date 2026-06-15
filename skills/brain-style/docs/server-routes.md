# Server Route Style

## Contents

- [Default to Resource-Oriented REST](#default-to-resource-oriented-rest)
- [Route Design Rules](#route-design-rules)
- [Subresources and Relationships](#subresources-and-relationships)
- [Acceptable Action-Style Exceptions](#acceptable-action-style-exceptions)
- [Review Checklist](#review-checklist)

## Default to Resource-Oriented REST

When creating HTTP server routes, model the URL path as a resource identifier and let the HTTP method carry the operation.

```http
GET /users
POST /users
GET /users/{userId}
PATCH /users/{userId}
DELETE /users/{userId}
```

Prefer this over encoding the operation as a query string, request body instruction, or verb-like route name.

```http
# Avoid when a standard resource route works
POST /users?action=delete&id=123
POST /users/delete
POST /users
{ "operation": "delete", "id": "123" }
```

Use these terms when explaining the choice:

- "RESTful" or "resource-oriented" for the preferred style.
- "RPC-style", "action-style", or "instruction-style" for command-shaped alternatives.
- "Uniform interface" for the REST principle behind using standard HTTP methods.

## Route Design Rules

Use nouns for resources and stable identifiers in path parameters.

```http
# Prefer
GET /projects/{projectId}/members
PATCH /projects/{projectId}/members/{memberId}

# Avoid
POST /projects/getMembers
POST /projects/updateMember
```

Choose the narrowest standard method that matches the operation:

| Method | Use for |
|--------|---------|
| `GET` | Read a resource or collection without side effects |
| `POST` | Create a subordinate resource or trigger a non-idempotent process |
| `PUT` | Replace an entire resource at a known URL |
| `PATCH` | Partially update a resource |
| `DELETE` | Remove a resource or relationship |

Put selectors, filters, pagination, sorting, and sparse-field options in the query string. Do not put commands there.

```http
# Correct query usage
GET /projects?status=active&limit=50

# Avoid command query usage
POST /projects?command=archive
```

Put resource state or creation/update input in the body. Do not use body fields like `action`, `operation`, or `method` to choose the endpoint behavior when the method and path can express it.

## Subresources and Relationships

Represent relationships as resources when clients need to manage them directly.

```http
GET /projects/{projectId}/members
PUT /projects/{projectId}/members/{userId}
DELETE /projects/{projectId}/members/{userId}
```

For nested paths, stop when the route still names a clear resource. Avoid deep paths that expose implementation joins or make ownership ambiguous.

```http
# Usually enough
GET /comments/{commentId}

# Usually too coupled
GET /organizations/{orgId}/projects/{projectId}/tasks/{taskId}/comments/{commentId}
```

## Acceptable Action-Style Exceptions

Use an action-style route only when no durable resource or standard method maps cleanly to the behavior. Good exceptions include:

- Process commands: `POST /imports/{importId}/cancel`
- Domain operations that are not CRUD: `POST /invoices/{invoiceId}/void`
- Ephemeral calculations: `POST /quotes/price-preview`
- Authentication/session conventions already established by the project: `POST /sessions`, `DELETE /sessions/current`, or existing equivalents

Even then, prefer naming the result as a resource when possible.

```http
# Prefer if the operation creates a durable job
POST /exports
GET /exports/{exportId}

# Accept only if it is truly command-like and existing project style supports it
POST /reports/{reportId}/regenerate
```

## Review Checklist

Before adding or approving a route:

1. Identify the resource or relationship being read, created, updated, or deleted.
2. Check whether a standard HTTP method plus noun path expresses the behavior.
3. Use query parameters only for selection modifiers, not instructions.
4. Use request bodies for representation data, not endpoint dispatch.
5. Match existing project route conventions unless they conflict with the resource-oriented default.
6. If choosing action-style, explain why a resource-oriented route would be misleading or awkward.
