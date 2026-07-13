# Where capability files live

Use the layout declared by the host project. Existing capability files and `AGENTS.md` or `CLAUDE.md` are authoritative; this skill supports two common patterns.

## Co-located layout

Place `capabilities.md` next to the code it describes. This works well when directory boundaries correspond to user-perceivable surfaces.

Examples:

```text
apps/web/src/app/login/capabilities.md
apps/web/src/app/api/session/capabilities.md
apps/mobile/src/features/auth/capabilities.md
apps/mobile/src/screens/LoginScreen/capabilities.md
```

Use route-level files for user-facing pages, endpoint-level files for API contract semantics, feature-level files for cross-screen flows, and screen-level files for local actions. Overlap is acceptable when the files describe different vantage points.

## Centralized layout

Place capability documents under a project-declared tree when logical product structure matters more than source layout.

Example:

```text
docs/capabilities/
  routes/login.md
  api/session.md
  features/auth.md
  screens/login.md
```

Choose namespaces that match the project. Do not assume that routes, screens, or APIs exist in every project.

## Adoption rule

Do not mix layouts accidentally. When adopting this convention:

1. Choose co-located or centralized files.
2. Record the roots and naming rules in `AGENTS.md` or `CLAUDE.md`.
3. Add the matching Documentation Sync glob.
4. Treat an intentional layout migration as separate work with an explicit cutover.

## Scope decisions

- Give a file to a user-perceivable surface, flow, or contract—not every source file.
- Skip pass-through layouts, purely presentational helpers, loading placeholders, and infrastructure with no meaningful user-facing behavior.
- Document shared components only when they carry behavior worth maintaining independently.
- Keep direct references inside one repository. Use the optional product-layer protocol for cross-repository alignment.

See `route-edge-cases.md` for routed-application guidance.
