# Routed-application edge cases

Apply these rules only when the project uses a file-based router with equivalent concepts. Follow the framework and host project's conventions when they differ.

## Route groups

Route groups such as `(marketing)` or `(authenticated)` often organize shared layouts without appearing in the URL. Skip a group-level capability file unless the group itself adds user-facing behavior. Document the routes inside it.

## Loading and error files

Loading, error, and leaf not-found files normally defer to the surrounding route's capability document. Give one a separate capability entry only when it introduces meaningful behavior beyond displaying state or retrying a failed load.

## Layouts

A pass-through layout needs no capability file. A layout that adds navigation, global search, an account menu, or another independent action should document that behavior at the layout level.

## Dynamic and catch-all segments

A dynamic segment such as `users/[userId]` usually represents one kind of user-perceivable page and shares one capability document. Describe the parameter abstractly. Split documentation only when parameter values produce materially different surfaces.

Apply the same rule to catch-all segments such as `[...slug]`.

## Parallel and intercepting routes

When a route renders in a named slot, mention the slot's contribution in the surrounding surface. Give the slot its own document only when it has independent behavior.

When navigation can render the same resource as a modal or standalone page, use separate capability headings if the experiences materially differ.

## Multiple HTTP methods

For an endpoint exposing multiple methods, use at least one `## <METHOD>: <action>` heading per method. A method may have both supported and omitted entries when documenting the boundary is useful.

```markdown
## POST: Create a session
## DELETE: Revoke a session
```

## Middleware

Middleware normally has no user-facing surface of its own. Document its effect in each affected route, such as a sign-in requirement or redirect. Create a dedicated capability document only when the host project's centralized layout explicitly treats middleware as a capability namespace.

## Default decision

Prefer one document per user-perceivable surface. If users cannot tell two source routes apart, combine them. If users experience meaningfully different actions, conditions, or outcomes, separate them.
