# Where capabilities files live

Each `capabilities.md` is co-located with the code it describes. There is no central registry of capability files in any consuming repo — agents discover them via the filesystem.

## Server (`proposit-server`)

### User-facing routes

`proposit-server/src/app/<route>/capabilities.md` next to each route folder under `src/app/`. The file describes what an end-user can do on that route.

Route groups like `(nofooter)` and `(withfooter)` are pass-through and do **not** get their own file. The route folders *inside* the group (e.g., `(nofooter)/login/`) are what get capability files.

### API routes

`proposit-server/src/app/api/<endpoint>/capabilities.md` next to each `route.ts`. The file describes what an API client can do, what the endpoint enforces, and what it explicitly does not do — capturing contract *semantics* on top of the TypeBox request/response schemas (which live in `@proposit/shared`).

An API route's `capabilities.md` uses one or more `## <METHOD>: <action>` headings — at least one per HTTP method the route exports, plus additional `Omitted` headings to declare what the endpoint deliberately does not do. See `docs/exemplars/server-api-endpoint.md`.

## Mobile (`proposit-mobile`)

### Feature folders

`proposit-mobile/src/<feature>/capabilities.md` for cross-screen feature flows (`auth`, `arguments`, `reviews`, etc.). The file describes the user's journey across screens, persistence, and feature-level guarantees.

### Screen components

`proposit-mobile/src/screens/<Screen>/capabilities.md` for screen-local capabilities — what the user does on this specific screen. The screen-component convention (folder layout, what counts as a "screen" vs. a helper component) is whatever `proposit-mobile/CLAUDE.md` defines; this skill mirrors that convention.

### Overlap is acceptable

A capability that involves multiple screens (e.g., the OAuth handshake) appears in both the feature-folder file and the relevant screen-component file. The screen file describes the concrete user actions on that screen; the feature file describes the cross-screen context. Both can describe the same capability — they have different vantage points. Same-repo references between them using `<path>#<heading-slug>` are allowed.

## What is *not* in scope

- **Cross-repo links from per-repo files.** A `capabilities.md` in `proposit-server` does not link to or reference a path in `proposit-mobile` (or vice versa). The orchestrator handles cross-repo coordination (see `docs/product-layer-coordination.md`).
- **Pure infra files.** `loading.tsx`, `error.tsx`, leaf `not-found.tsx` defer to the parent route's `capabilities.md`. They don't get their own file.
- **Helper components.** Mobile components that aren't screens (e.g., shared form fields, buttons, modals) don't get capability files unless they carry meaningful user-facing behavior on their own.
- **Layouts.** A layout that adds user-facing capabilities of its own (e.g., a global search bar in `layout.tsx`) gets a `capabilities.md` next to the layout file. A layout that only renders its children does not.

See `docs/route-edge-cases.md` for additional server-route edge cases (dynamic segments, parallel routes, intercepting routes, catch-alls).
