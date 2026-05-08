# Upcoming

## Added

- New skill `capabilities-sdlc` at `skills/capabilities-sdlc/`. Provides the conventions for documenting user-facing capabilities of Proposit applications.
  - `SKILL.md` — routing layer with auto-load triggers and reference table.
  - `docs/file-locations.md` — where `capabilities.md` files live in `proposit-server` and `proposit-mobile`.
  - `docs/format.md` — file format spec, conventions, reference style (heading anchor + path).
  - `docs/statuses.md` — three-status taxonomy with body-content rules per status.
  - `docs/planning-gate.md` — `## Capability changes` rule + bug-fix and discovery-fix exceptions.
  - `docs/broker-protocol.md` — product-layer DM protocol + broker-unavailable fallback.
  - `docs/route-edge-cases.md` — server route enumeration (route groups, layouts, dynamic segments, etc.).
  - `docs/exemplars/{server-user-route,server-api-endpoint,mobile-feature-folder,mobile-screen}.md` — fully-written gold-standard files.
- `capabilities-sdlc` added to `plugin.json` keywords array.
