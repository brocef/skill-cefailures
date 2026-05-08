# Server route edge cases

This is the canonical enumeration of edge cases for `proposit-server`'s `src/app/` tree. The base rule is in `docs/file-locations.md`: each user-facing route folder gets a `capabilities.md`. This document covers the cases where the base rule needs interpretation.

## Route groups (`(name)`)

Route groups like `(nofooter)`, `(withfooter)`, `(auth)` are pass-through. They do not appear in the URL and exist only to share layouts. **Skip them — they don't get their own `capabilities.md`.** The route folders *inside* the group (e.g., `(nofooter)/login/`) are what get capability files.

## Pure infra files

`loading.tsx`, `error.tsx`, leaf `not-found.tsx` are infra. **They do not get their own `capabilities.md` files.** They defer to the parent route's file. If the loading or error UI carries a meaningful user-facing capability beyond "show a spinner" or "show 'something went wrong'", that capability is described in the parent route's file.

## Layouts

`layout.tsx` files are usually pass-through (they wrap children with shared chrome) and do not get their own `capabilities.md`.

The exception: a layout that adds user-facing capabilities of its own — e.g., a global search bar, a navigation menu with its own actions, an account dropdown — gets a `capabilities.md` next to the `layout.tsx`. The capabilities file describes only the layout-introduced behavior, not the children's.

## Dynamic segments (`[param]`)

A dynamic segment like `src/app/users/[userId]/` shares its parent's `capabilities.md`, since the user-facing experience is the *kind of page* (a user profile), not the specific value. The capability description treats the dynamic value abstractly: "the user views the profile of any user identified by URL".

The exception: when the dynamic segment renders a materially different surface depending on the parameter (e.g., `[type]` where each type is a different page experience), give the dynamic segment its own folder structure with its own `capabilities.md`.

## Catch-all segments (`[...slug]`)

`[...slug]` segments behave like dynamic segments for capability purposes. Share the parent's file unless the catch-all surface is materially distinct.

## Parallel routes (`@slot`)

Parallel routes render alongside the main route in named slots. The capability description for the main route mentions the slot's contribution. The slot folder itself does not get a separate `capabilities.md` unless the slot has independent user-facing behavior worth describing.

## Intercepting routes (`(.)`)

Intercepting routes (e.g., `(.)photo/[id]/`) render different content based on navigation context. They typically share the intercepted route's `capabilities.md`. If the intercepted view is materially different from the standalone view, document both with `## ...` headings in one file (e.g., `## View photo (modal)` and `## View photo (standalone)`).

## API routes with multiple HTTP methods

A `route.ts` exporting multiple HTTP methods produces multiple `## ...` headings in one `capabilities.md`. Use the form `## <METHOD>: <action>`:

```markdown
## POST: Validate Google ID token and start session
## DELETE: Revoke session
```

See `docs/exemplars/server-api-endpoint.md` for a fully-written example.

## Middleware

Middleware (`middleware.ts`) does not get its own `capabilities.md`. Middleware behavior is described in the routes whose user-facing experience it affects. For example, an auth middleware that redirects unauthenticated users to `/login` is mentioned in the protected routes' capabilities ("This page requires sign-in; unauthenticated users are redirected to `/login`").

## When the rule is unclear

When two readings of the rule are both reasonable, default to **one file per user-perceivable surface**. If the user can't tell that two routes are different (same URL, same chrome, same actions), one file. If they perceive a meaningfully different experience, separate files.
