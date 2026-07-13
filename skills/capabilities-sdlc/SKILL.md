---
name: capabilities-sdlc
description: Use when authoring, updating, planning, or reviewing user-capability documentation in any project. Applies to capability files co-located with routes, screens, features, components, or API endpoints, and to centralized capability trees declared by the host project. Use when planning user-facing feature changes or checking whether documented capabilities match implementation.
---

# capabilities-sdlc

Maintain natural-language records of intended user-facing behavior without assuming a particular repository layout, application stack, or coordination system.

## Core workflow

1. Read the host project's `AGENTS.md` or `CLAUDE.md` and existing capability files to discover its chosen layout and documentation-sync rules.
2. For a plan or specification that changes intended user behavior, open with `## Capability changes`. See `docs/planning-gate.md`.
3. Author capability entries using the three-status format in `docs/format.md` and `docs/statuses.md`.
4. Before completing implementation, compare the change with existing capability entries and surface contradictions. See `docs/contradiction-detection.md`.
5. Use product-layer coordination only when the host workspace declares a shared product layer. See `docs/product-layer-coordination.md`.

## Reference table

| Doc | Read when |
|-----|-----------|
| `docs/file-locations.md` | Choosing or discovering co-located versus centralized capability files. |
| `docs/format.md` | Authoring a capability file or same-repository reference. |
| `docs/statuses.md` | Selecting `Supported`, `Missing`, or `Omitted`. |
| `docs/planning-gate.md` | Writing a brainstorm, spec, plan, or briefing for user-facing work. |
| `docs/contradiction-detection.md` | Changing behavior already described by a capability entry. |
| `docs/product-layer-coordination.md` | Coordinating wording across repositories in a workspace that declares a product layer. |
| `docs/route-edge-cases.md` | Mapping routed applications, including Next.js-style route structures, to capability files. |
| `docs/exemplars/server-user-route.md` | Example user-facing web route. |
| `docs/exemplars/server-api-endpoint.md` | Example multi-method API endpoint. |
| `docs/exemplars/mobile-feature-folder.md` | Example cross-screen feature. |
| `docs/exemplars/mobile-screen.md` | Example screen-local behavior. |

## File format

```markdown
# <Subject> — capabilities

## <Capability name>
**Status:** Supported | Missing | Omitted

<1–3 short paragraphs; body rules vary by status.>
```

Use no frontmatter or formal IDs. Keep references inside the same repository; coordinate cross-repository intent through the host workspace rather than direct links.

## Adoption contract

Do not invent capability roots or globs. Follow existing files and host instructions. If a project is adopting the convention for the first time, have the user choose a layout and record it in `AGENTS.md` or `CLAUDE.md` before creating files.

For a co-located layout, a typical Documentation Sync entry is:

```markdown
- `**/capabilities.md` [User-Capabilities] — User-capability docs co-located with code.
  The trigger fires when behavior in the same directory or subtree changes.
```

For a centralized layout, use the project's declared root, for example:

```markdown
- `docs/capabilities/**/*.md` [User-Capabilities] — Central user-capability catalog.
  The trigger fires when documented user-facing behavior changes.
```

## Boundaries

- Do not define product intent on the user's behalf; document decisions made from code, plans, and user direction.
- Do not require an orchestrator, broker, product layer, or multi-repository workspace.
- Do not silently reconcile contradictions between code and capability documents.
- Do not use capability status to track regressions; use the project's bug tracker or follow-up log.
