---
name: capabilities-sdlc
description: Use when authoring or updating user-capability documentation (`capabilities.md` files) co-located with route folders, screen components, feature folders, or API endpoints. Use when planning, brainstorming, or specifying any user-facing feature change. Use when reviewing whether a `capabilities.md` is in sync with the code it describes.
---

# capabilities-sdlc

Documents the conventions for the Proposit capabilities-SDLC: how user-facing capabilities are described in markdown files co-located with the code they describe, what the planning gate is, and how cross-repo capability drift is avoided.

## When this skill applies

- A `capabilities.md` file exists or is being authored for a route, screen, feature folder, or API endpoint in a Proposit repo.
- A brainstorm, spec, plan, or briefing is being written for user-facing feature work.
- A reviewer is checking whether documented capabilities match the implementation.

## The planning gate (one-line summary)

Every brainstorm, spec, plan, or briefing for user-facing work opens with a `## Capability changes` section as its first content section. See `docs/planning-gate.md` for the full rule, including the bug-fix carve-outs (regression vs. discovery vs. capability-change-disguised-as-bug-fix).

## Reference table

| Doc | Scope |
|-----|-------|
| `docs/file-locations.md` | Where `capabilities.md` files live in `proposit-server` and `proposit-mobile`, and what is *not* in scope for capability documentation. |
| `docs/format.md` | The skeleton, conventions, and reference style for a single capability and a single file. |
| `docs/statuses.md` | The three-status taxonomy (`Supported`, `Missing`, `Omitted`) with body-content rules and the rejected-fourth-status note. |
| `docs/planning-gate.md` | The `## Capability changes` requirement for plans and specs, including the bug-fix and discovery-fix exceptions. |
| `docs/product-layer-coordination.md` | How per-repo agents query the orchestrator for product-layer wording, and the coordination-unavailable fallback. Transport-agnostic. |
| `docs/route-edge-cases.md` | Server route enumeration: route groups, infra files, layouts, dynamic segments, catch-alls, parallel and intercepting routes, multi-method API routes, middleware. |
| `docs/exemplars/server-user-route.md` | Fully-written exemplar for a server user route (`/login`-style). |
| `docs/exemplars/server-api-endpoint.md` | Fully-written exemplar for a server API endpoint (multi-method case). |
| `docs/exemplars/mobile-feature-folder.md` | Fully-written exemplar for a mobile feature folder (cross-screen flows). |
| `docs/exemplars/mobile-screen.md` | Fully-written exemplar for a mobile screen component (screen-local). |

## Two-layer model (one-line summary)

- **Per-repo layer.** `capabilities.md` co-located with code in each consuming repo. Per-repo files do not link to or reference anything outside their repo.
- **Shared product layer.** `proposit-orchestration/docs/capabilities/<area>.md`, owned by the orchestrator. Per-repo agents do not read this layer; the orchestrator relays product-layer wording on request (see `docs/product-layer-coordination.md`).

## File format (one-line summary)

```markdown
# <Subject> — capabilities

## <Capability name>
**Status:** Supported | Missing | Omitted

<1–3 short paragraphs of body content; rules vary by status — see docs/statuses.md.>
```

No frontmatter. No formal IDs. No cross-repo links from per-repo files.

## Documentation Sync entry (copy-paste)

Every consuming repo's `CLAUDE.md` should include this entry under its `## Documentation Sync` section so that capability files are kept in sync with code changes:

```
- `**/capabilities.md` [User-Capabilities] — Per-route/screen/feature user-capability docs.
  The trigger fires when a code change in the same directory or its subtree alters
  user-facing behavior. The `skill-cefailures:capabilities-sdlc` skill describes the format,
  status taxonomy, and the planning-gate rule.
```

The `**/capabilities.md` glob is intentional and unusual — most existing doc-sync entries name a single concrete path. Reviewers evaluate this trigger against any matching file in the diff.

## What this skill does *not* do

- It does not define product-level capability content. The orchestrator owns `proposit-orchestration/docs/capabilities/<area>.md`; per-repo agents do not read those files.
- It does not enforce the planning gate via lint or CI. Enforcement is convention: this skill, the orchestration `CLAUDE.md`, and per-repo `CLAUDE.md` notes.
- It does not track bugs or regressions. Capability files describe *intended* state; bug-tracking happens elsewhere (e.g., per-repo `FOLLOWUPS.md`).
