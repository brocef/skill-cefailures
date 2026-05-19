# Capabilities SDLC v2 — design

**Status:** Approved (brainstorm complete; awaiting implementation plan)
**Scope:** Replace the existing `capabilities-sdlc` skill with a project-agnostic v2 that expands the file layout, status taxonomy, cross-reference grammar, sidecar conventions, and external-tracker integration. Proposit's per-repo migration is a separate slice.

> This spec is a meta-document about the `capabilities-sdlc` skill itself; the `## Capability changes` planning gate is therefore not applicable to this file. The gate continues to apply to specs *authored under* the v2 skill in projects that adopt it.

## Goals

A project that adopts v2 of this skill gets:

1. **A living, natural-language source of truth** for every documented user-facing capability — what the user can do, the state of the world that makes the capability available, and the lifecycle of the capability over time. Documents are written in natural language because (a) they're easier to read than code, (b) change requests are written in natural language anyway, and (c) AI agents and humans alike use them as a baseline to audit code and tests.
2. **A discoverable catalog** rooted at `docs/capabilities/`. Folder names are self-documenting; the layout is the routing.
3. **Cross-references that are short, stable, and grep-able** — identifier form like `components/complex-styled-button[icon]#tap-and-release`.
4. **Statuses that distinguish lifecycle from intent** — five primary statuses, plus an optional lifecycle modifier and an orthogonal priority axis.
5. **Sidecars for enumerable data** — error catalogs and state catalogs sit next to the capability file they describe.
6. **App-level globals** — roles and conditions are first-class top-level namespaces; capability metadata fields reference them by slug.
7. **A future-proof tracker convention** — capabilities reference Jira/GitHub/Linear by shortname; v3 can layer sync without changing the format.

## Non-goals

These are deliberately out of scope for v2:

- **Version qualifiers in cross-refs** (`@<git-ref>`) — needs a git-aware resolver; no concrete use case yet. Deferred to v3.
- **Tracker sync** — adapters per tracker (Jira API, GitHub Issues API, Linear API) with auth and conflict reconciliation. Designed-for, not built. Deferred to v3.
- **CI/lint enforcement** of format, cross-refs, and shortname resolution. The skill remains convention-only; reviewer attention and the contradiction-detection rule are the backstop.
- **Additional sidecar types** beyond `errors.md` and `states.md`. Events, metrics, and others wait for concrete pull from a real project.
- **Cross-repo references** from per-repo capability files. Per-repo files still don't reference paths in other repos. The orchestrator-coordinated product layer remains the only cross-repo bridge for projects that need one.
- **Full boolean expressions** in `**Roles:**` / `**When:**`. Complex policies stay in prose.
- **Required document sections** beyond `# <Subject> — capabilities` and the `## Capability` headings. Optional sections (`## Cross-references`, `## Open questions`) are recommended but not mandatory.
- **Bundled migration tooling** for the existing Proposit per-repo `capabilities.md` files. Migration is its own per-repo plan, written after the v2 skill ships.

---

## 1. File layout

### 1.1 The parallel `docs/capabilities/` tree

All capability documentation in an adopting project lives in a single tree rooted at `docs/capabilities/`. Files are **not** co-located with code. The tree's structure is the project's logical structure — what is the project made of? Top-level folders are the answer.

### 1.2 Namespaces (open-ended)

Top-level folders under `docs/capabilities/` are *namespaces*. The skill recommends an illustrative starter set:

- `routes/` — user-facing pages or routes.
- `components/` — reusable UI components.
- `features/` — cross-screen or cross-page flows.
- `api/` — HTTP endpoints, gRPC methods, message handlers.
- `roles/` — app-level role definitions.
- `conditions/` — named runtime conditions (`authed`, `email-verified`, etc.).

Projects extend this set as needed (`jobs/` for cron workers, `cli/` for CLI commands, `webhooks/` for inbound webhooks, etc.) and document the chosen namespaces in the project's `CLAUDE.md`. The skill does not prescribe a fixed list — different project shapes need different vocabularies.

### 1.3 File-vs-folder rule

A capability is a **flat file** by default: `components/footer.md`. Promote to a **folder** with an entry doc named exactly `capabilities.md` only when sibling files are required:

- State-variant capability files (see §1.4),
- Sidecars (`errors.md`, `states.md` — see §5),
- Sub-capabilities that warrant their own files (rare).

Examples:

```
docs/capabilities/
├── components/
│   ├── footer.md                                    # simple → flat
│   └── complex-styled-button/                       # has variants → folder
│       ├── capabilities.md                          # common-state capabilities
│       ├── with-icon.md                             # icon-variant capabilities
│       ├── without-icon.md                          # non-icon-variant capabilities
│       └── states.md                                # sidecar: button states
├── api/
│   └── auth/
│       └── login/                                   # has sidecar → folder
│           ├── capabilities.md
│           └── errors.md
├── routes/
│   ├── login.md
│   └── profile.md
├── roles/
│   ├── admin.md
│   ├── owner.md
│   └── user.md
└── conditions/
    ├── authed.md
    └── email-verified.md
```

### 1.4 State-variant files

When a capability folder has state-aware behavior (a button with/without an icon; a screen in draft vs. published modes), state-specific capabilities go in sibling files named by convention:

- **Affirmative state**: `with-<state>.md` (e.g. `with-icon.md`)
- **Negated state**: `without-<state>.md` (e.g. `without-icon.md`)
- **The entry doc** (`capabilities.md`) holds capabilities that are common to *all* state variants.

The state slug (`icon`) is what cross-ref `[state]` qualifiers resolve to (see §4). The default `with-`/`without-` prefix is overridable per-project via the `state-conventions:` section of `.config.yaml` (see §6), but most projects should leave it at the default.

---

## 2. Document format

### 2.1 Skeleton

```markdown
# <Subject> — capabilities

## <Capability name>
**Status:** Supported
**Priority:** P1
**Lifecycle:** Experimental
**Tracker:** jira:PROJ-123
**Roles:** admin, owner
**When:** authed, !banned

<1–3 short paragraphs: user-perspective trigger, behavior, outcome.>

## <Another capability>
**Status:** Missing
**Priority:** P2
**Tracker:** jira:PROJ-456

<Why we want it; what unblocks it.>

## Cross-references

- `components/complex-styled-button[icon]`
- `roles/admin`

## Open questions

- Should the action be available to `editor` role as well? (See `roles/editor`.)
```

### 2.2 Rules

- **Top heading**: `# <Subject> — capabilities`. The subject names what the file is about (route name, screen name, feature name, API endpoint path, component name).
- **One `## Capability` per discrete user action**, in natural-language imperative form ("Sign in with Google", not "googleSignIn" or "Login Capabilities").
- **Inline metadata block**: every `**Field:** value` line stacks immediately under the `## Capability` heading with no blank line between the heading and the first metadata line. Body content starts after the metadata block + one blank line.
- **Body length**: 1–3 short paragraphs. If a capability needs more, it's probably two capabilities.
- **API endpoint capabilities**: use `## <METHOD>: <action>` form (`## POST: Validate Google ID token and start session`). Carried over from v1.
- **No file-level YAML frontmatter**. Per-capability inline metadata is sufficient and visually cleaner.
- **Optional sections** after capabilities: `## Cross-references` and `## Open questions`. Not required.

### 2.3 The full set of metadata fields

| Field | Required? | Applies to | Format |
|-------|-----------|------------|--------|
| `**Status:**` | Yes | All | One of `Supported` / `Partial` / `Missing` / `Blocked` / `Omitted` |
| `**Priority:**` | No | All | One of `P0` / `P1` / `P2` / `P3` |
| `**Lifecycle:**` | No | `Supported` / `Partial` only | One of `Experimental` / `Stable` / `Deprecated` |
| `**Superseded by:**` | Required when `Lifecycle: Deprecated` and a successor exists | `Supported` / `Partial` with `Deprecated` lifecycle | A cross-reference identifier |
| `**Tracker:**` | No | All | Comma-separated `<shortname>:<id>` list |
| `**Roles:**` | No | All | Comma-separated list of `roles/` slugs (OR-ed within field) |
| `**When:**` | No | All | Comma-separated list of `conditions/` slugs (AND-ed within field), `!` prefix negates |
| `**Gaps:**` | Required when `Status: Partial` | `Partial` only | Comma-separated list or sub-bullets of known holes |
| `**Blocked by:**` | Required when `Status: Blocked` | `Blocked` only | Concrete dependency: cross-ref identifier, external system name, or unresolved decision |

Unrecognized field names are skill violations to surface in review. The skill ships with this fixed set; future fields require a skill version bump.

---

## 3. Statuses, lifecycle, and priority

### 3.1 Statuses (5, locked)

- **`Supported`** — works today. Default for any documented capability that is implemented. Body describes user-perspective trigger and outcome.
- **`Partial`** — supported with explicitly enumerated gaps. Body describes what works; `**Gaps:**` field lists what doesn't. Different from `Supported` with prose caveats: gaps must be enumerable so reviewers and tooling can spot when a gap has been closed (status flips to Supported) or expanded (gaps list grows).
- **`Missing`** — desired but not built. Body explains why desired and what unblocks. If a planned initiative will deliver it, name the initiative. If a specific blocker exists (an endpoint, a dependency, a decision), name it.
- **`Blocked`** — desired but cannot start because of a specific, identified external dependency. Body explains why desired; `**Blocked by:**` names the blocker concretely. Distinguished from `Missing` by *active* blockage: a Missing capability could be picked up tomorrow; a Blocked one cannot until its dependency clears.
- **`Omitted`** — deliberately not supported. Body explains the rationale and (if applicable) where the alternative lives.

### 3.2 Status vocabulary is locked

Additions to the five-status set require a skill version bump and an explicit rationale, mirroring v1's rejected-fourth-status note. The five-status set was chosen specifically to resist the universal pitfall the prior-art survey flagged: status taxonomies inflate ("teams start with 3 statuses, end with 17"). If you find yourself wanting a sixth status, the answer is almost always "use Lifecycle or Priority instead."

In particular:

- **No `Broken` status.** Capability files describe *intended* state. A `Supported` capability that's broken in production is a bug — track it in `FOLLOWUPS.md`, GitHub issues, Jira, etc. The intent doesn't change.
- **No `In progress` status.** That's tracker territory. A capability that's `Missing` with a `**Tracker:**` pointing to an in-flight ticket conveys the same information.

### 3.3 Lifecycle (optional, on Supported/Partial)

Three values. The default is Stable and can be omitted.

- **`Experimental`** — works but unstable. Behind a feature flag, internal-only, or otherwise not for general use. Body should note the gating mechanism.
- **`Stable`** — production-ready. Default; usually omitted.
- **`Deprecated`** — works but being phased out. **Must carry `**Superseded by:** <identifier>`** if there's a successor capability. Without a successor, the body explains the removal path.

Lifecycle is orthogonal to status. A capability can be `Status: Partial, Lifecycle: Deprecated` — partially supported, being phased out — though most real capabilities live in fewer combinations.

### 3.4 Priority (optional)

Four values: `P0` (critical) / `P1` (high) / `P2` (normal) / `P3` (low). Optional. When omitted, no priority is asserted.

Priority is most useful on `Missing`, `Blocked`, and `Partial` capabilities — it's how the backlog sorts itself. On `Supported` capabilities, priority answers "if regressions arrive, which one do we fix first?" — useful for triage but often omitted in practice. On `Omitted`, priority is rarely meaningful (an omitted capability is not on a roadmap).

Projects with strong existing prioritization frameworks (MoSCoW, t-shirt sizes) can map them to P0–P3 in their `CLAUDE.md`. The skill does not support alternative priority vocabularies in the format itself, again to resist taxonomy inflation.

---

## 4. Cross-references

### 4.1 Grammar

The full identifier-based grammar:

```
<namespace>/<path>[state][#heading-slug]
```

Where:

- **`<namespace>/<path>`** is the identifier, resolved relative to `docs/capabilities/`. The leaf may be either a flat file or a folder containing `capabilities.md`. So `components/footer` resolves to `docs/capabilities/components/footer.md`; `components/complex-styled-button` resolves to `docs/capabilities/components/complex-styled-button/capabilities.md`.
- **`[state]`** (optional) picks a state-variant sibling file in the same folder, using the project's state convention. By default, `[icon]` → `with-icon.md`, `[!icon]` → `without-icon.md`, `[*]` → "applies to all state-variant files in the folder, fanned out". An identifier without a state qualifier refers to the common capabilities in the entry doc (`capabilities.md`), not "all states."
- **`#heading-slug`** (optional) is a GitHub-flavored slug of a `## Capability` heading inside the resolved file. Lowercase, words joined by hyphens, punctuation stripped. The same form GitHub renders.
- **Whitespace** is not allowed anywhere in an identifier.

### 4.2 Resolution order

The leaf of `<namespace>/<path>` is resolved in this order:

1. **Flat file** — if `docs/capabilities/<namespace>/<path>.md` exists, use it.
2. **Folder with entry doc** — if `docs/capabilities/<namespace>/<path>/` is a folder containing `capabilities.md`, use that `capabilities.md`.

If both exist for the same path, that's an authoring error to surface in review. In practice this collision is what makes the "promote to folder" rule (§1.3) a *rename* of the flat file into the folder rather than an addition alongside it.

Sidecar references work through case (1): writing `api/auth/login/errors` resolves to `docs/capabilities/api/auth/login/errors.md` (the `errors.md` sidecar sitting next to `capabilities.md` inside the `login/` folder). The grammar doesn't need a separate "this is a sidecar" syntax — sidecar files are just flat files with reserved names.

The `[state]` qualifier always applies *after* the leaf resolves; it picks a sibling file in the same folder as the resolved file. State qualifiers on a flat-file leaf are an authoring error (`components/footer[hover]` is invalid because `components/footer.md` has no folder to look in).

### 4.3 Examples

| Identifier | Resolves to |
|------------|-------------|
| `components/footer` | `docs/capabilities/components/footer.md` (all capabilities) |
| `components/complex-styled-button` | `docs/capabilities/components/complex-styled-button/capabilities.md` (common-state capabilities) |
| `components/complex-styled-button[icon]` | `docs/capabilities/components/complex-styled-button/with-icon.md` |
| `components/complex-styled-button[!icon]` | `docs/capabilities/components/complex-styled-button/without-icon.md` |
| `components/complex-styled-button[*]` | All `with-*.md` / `without-*.md` files in the folder |
| `components/complex-styled-button#tap-and-release` | The `## Tap and release` capability in `capabilities.md` |
| `components/complex-styled-button[icon]#tap-and-release` | The same heading in `with-icon.md` |
| `api/auth/login#post-validate-credentials` | A specific method heading in the login endpoint |
| `api/auth/login/errors#401-invalid-credentials` | A specific error case in the sidecar |
| `roles/admin` | The admin role definition |
| `conditions/authed` | The authed condition definition |

### 4.4 Same-file references

Inside a file, references to other headings in the same file may use anchor-only form: `#sign-in-with-google`. Cross-file references must use the full identifier.

### 4.5 Validation

Validation is convention-only in v2. The skill describes the grammar; reviewer attention catches unresolvable identifiers. Future v3 tooling can lint cross-references against the file system without changing the format.

---

## 5. Sidecars

### 5.1 Types

Two first-class sidecar types in v2, both markdown with the same skeleton as `capabilities.md`:

- **`errors.md`** — colocated with a capability folder for any capability that has enumerable failure modes. Most commonly an API endpoint. Each `## <code>: <name>` heading is an error case.
- **`states.md`** — colocated with a capability folder for UI components or state-machine-like capabilities. Each `## <state-name>` heading describes a state.

Both files reuse the document-format rules from §2: top heading `# <Subject> — <type>` (e.g. `# /api/auth/login — errors`), `##` headings with inline metadata blocks, 1–3-paragraph bodies. Status semantics for sidecars:

- **`errors.md` entries**: usually `Supported` for active error cases, `Missing` for error cases that should exist but aren't surfaced yet, `Omitted` for cases the endpoint deliberately doesn't distinguish.
- **`states.md` entries**: status is usually omitted on `states.md` headings since states are descriptive, not lifecycle-tracked. A state being added or removed can carry `**Status:** Missing` or `Omitted`.

### 5.2 Referencing sidecars

Sidecars are referenced by extending the identifier with the sidecar filename, since the leaf is no longer the implicit `capabilities.md`:

```
api/auth/login/errors#401-invalid-credentials
components/complex-styled-button/states#hover
```

The `.md` extension is implied — never written in identifiers.

### 5.3 Why these two

`errors.md` and `states.md` are the sidecar types that meet two tests: (a) the entries are *enumerable* (a discrete list rather than narrative prose), and (b) they're typically referenced *from* other capabilities (an endpoint capability mentions error cases; a UI capability mentions states). Other candidates considered and deferred:

- **`events.md`** — for components/endpoints that emit events. Deferred because the eventing concept varies wildly (analytics, websockets, webhooks, callbacks) and v2 doesn't have a representative project to anchor the format.
- **`metrics.md`** / **`telemetry.md`** — too project-specific.
- **`permissions.md`** — folded into `roles/` and `conditions/` at the top level instead. Permissions are inherently cross-capability; they don't sit naturally as a per-capability sidecar.

---

## 6. Configuration

### 6.1 `.config.yaml`

A project that uses trackers or wants to override defaults declares a `docs/capabilities/.config.yaml`. The file is optional; projects with no trackers and default conventions don't need one.

```yaml
trackers:
  jira: https://acme.atlassian.net/browse/{id}
  gh: https://github.com/acme/repo/issues/{id}
  linear: https://linear.app/acme/issue/{id}

namespaces:           # optional documentation of the project's namespace set
  routes: User-facing pages
  components: Reusable UI
  api: HTTP endpoints
  features: Cross-screen flows
  roles: Role definitions
  conditions: Named runtime conditions

state-conventions:    # optional override of the with-/without- default
  # Default is fine for almost every project; override only if your state slugs
  # collide with the default prefixes. Format: { affirmative: "...", negated: "..." }
```

### 6.2 Behavior without `.config.yaml`

- Tracker shortnames in `**Tracker:**` fields render as plain text; no URL substitution.
- Namespaces are inferred from the filesystem; the skill doesn't require declared documentation.
- State conventions use the default `with-`/`without-` prefixes.

### 6.3 What does NOT belong in `.config.yaml`

- Status taxonomy. Locked by the skill.
- Lifecycle vocabulary. Locked.
- Cross-reference grammar. Locked.
- Sidecar types. Locked.

`.config.yaml` is for *project-shaped* details (which trackers, which namespaces, which state conventions), never for redefining the skill's vocabulary.

---

## 7. Process gates

### 7.1 Planning gate

**Every brainstorm, spec, plan, or briefing for user-facing work opens with a `## Capability changes` section as its first content section.** Carried forward from v1, with the section's three buckets (New / Updated / Deleted) now including v2's expanded fields when relevant.

Example:

```markdown
## Capability changes

- **New:** `components/complex-styled-button[icon]` — adds the icon-variant capability file; declares "Tap and release" as `Supported`, `**Priority:** P1`.
- **Updated:** `routes/login#sign-in-with-google` — status flips from `Partial` to `Supported`; removes the `**Gaps:**` line.
- **Updated:** `api/auth/google#post-validate-google-id-token-and-start-session` — `**Lifecycle:** Experimental` removed; capability graduates to Stable.
- **Updated:** `components/complex-styled-button#tap-and-release` — `**Tracker:**` updated from `jira:PROJ-123` to `gh:456` after the work moved trackers.
- **Deleted:** `components/legacy-button` — body rewritten as `Omitted` with `**Superseded by:** components/complex-styled-button`.
```

Bug-fix carve-outs from v1 are unchanged:

- **Pure regression fix** (capability file says `Supported`, behavior previously worked, fix restores it): no gate. The intent didn't change.
- **Discovery fix** (capability says `Supported`, behavior never actually worked): gate applies. The documented intent is itself in question.
- **Capability change disguised as a bug fix**: gate applies.

When in doubt, run the gate.

### 7.2 Contradiction-detection rule

Carried forward from v1, expanded for v2. Before completing a code change that affects user-facing behavior, check whether the change contradicts any existing capability entry. If it does:

1. Surface the contradiction to the user — name the file, the capability, the current wording, and the specific conflict.
2. Ask which side moves — update the capability or revise the change.
3. Never silently update the capability file.

**Contradiction shapes (v2 expanded set).**

- **Status-flip** (carried forward) — code change conflicts with a documented Status value.
- **Scope** (carried forward) — code change broadens/narrows the user-roles or modes under which the capability fires.
- **Condition** (carried forward) — code change alters listed When conditions or other body-level enumerations.
- **Priority** (**new in v2**) — code implements something marked `Priority: P3` (deprioritized) without first changing the priority. Surface to confirm the prioritization is intentional.
- **Tracker mismatch** (**new in v2**) — capability's `**Tracker:**` ticket says "Done" but capability is still `Missing` (or vice versa). Surface during review; v2 has no automated sync, so reviewers spot these manually.
- **Roles/When tightening** (**new in v2**) — code change narrows the `**Roles:**` or `**When:**` set without updating the field.
- **Lifecycle mismatch** (**new in v2**) — code change extends a `Deprecated` capability without either undoing the deprecation or pointing the new behavior at the `Superseded by:` target.

The surfacing protocol and three valid resolutions (update the entry / revise the code / split into a new capability) are unchanged from v1.

---

## 8. Skill rollout (Approach A — replace in place)

The existing `skills/capabilities-sdlc/` directory is overwritten with v2 content. The following files change:

| File | Change |
|------|--------|
| `SKILL.md` | Rewritten: project-agnostic framing; new reference table; v1's Proposit-specific examples migrate to `docs/exemplars/`. |
| `docs/format.md` | Rewritten for the new metadata block, statuses, lifecycle, priority, sidecar conventions. |
| `docs/statuses.md` | Rewritten for the 5-value taxonomy + lifecycle + Gaps/Blocked-by/Superseded-by fields. |
| `docs/cross-references.md` | **New** — identifier grammar, state qualifiers, anchor rules, examples. |
| `docs/sidecars.md` | **New** — `errors.md` and `states.md` conventions, format, referencing. |
| `docs/globals.md` | **New** — `roles/` and `conditions/` namespaces; `Roles` and `When` grammar. |
| `docs/trackers.md` | **New** — `.config.yaml` schema; shortname form; sync deferral note. |
| `docs/planning-gate.md` | Updated examples for v2 metadata. Bug-fix carve-outs unchanged. |
| `docs/contradiction-detection.md` | Updated for new contradiction shapes. |
| `docs/file-locations.md` | Rewritten as project-agnostic explanation of the parallel `docs/capabilities/` layout. Proposit treated as one example. |
| `docs/product-layer-coordination.md` | Kept; reframed as one example of multi-repo product-layer coordination. |
| `docs/route-edge-cases.md` | Kept; reframed as advice for any routed app (Next.js or otherwise). |
| `docs/exemplars/server-user-route.md` | Kept; reframed as "Proposit-style example." |
| `docs/exemplars/server-api-endpoint.md` | Kept; reframed. |
| `docs/exemplars/mobile-feature-folder.md` | Kept; reframed. |
| `docs/exemplars/mobile-screen.md` | Kept; reframed. |
| `docs/exemplars/stateful-component.md` | **New** — a generic exemplar showing a stateful component with state-variant files and a `states.md` sidecar; demonstrates the full v2 surface. |
| `docs/exemplars/api-endpoint-with-errors.md` | **New** — generic API endpoint exemplar with an `errors.md` sidecar. |
| `docs/exemplars/role-and-condition.md` | **New** — generic exemplars for `roles/admin.md` and `conditions/authed.md` showing how globals look in practice. |

### 8.1 Repo versioning

Per this repo's convention, v2 is a `minor` bump (significant feature work). The version is carried in both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`; both bump together. `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` rotate to the new version per the documentation-sync skill.

### 8.2 Proposit migration (separate slice, not part of this spec)

The existing per-repo `capabilities.md` files in `proposit-server`, `proposit-mobile`, and the orchestrator's `docs/capabilities/` tree must move into the new parallel-tree layout in each repo and gain identifier paths. Each repo's `CLAUDE.md` Documentation Sync section needs the new glob (`docs/capabilities/**/*.md`).

**This is the orchestrator's job**, written as a per-repo plan in each Proposit repo after the v2 skill ships. The v2 skill spec records only:

- Consumers on v1 must migrate.
- Migration is bounded but per-repo.
- Do not mix layouts within a single repo (legacy co-located + new parallel-tree); pick one cutover moment per repo.

---

## 9. Risks and mitigations

- **Migration drag for Proposit.** Existing files must move; reviewers see both layouts during the cutover.
  *Mitigation:* Ship the skill first; migration is a follow-on plan with no time pressure. v2 lives alongside v1's deployed Proposit conventions until each repo migrates.
- **Status taxonomy creep.** Five statuses + lifecycle + priority is more axes than v1.
  *Mitigation:* `docs/statuses.md` opens with a one-line rule: "additions require a skill version bump and explicit rationale." Mirrors v1's rejected-fourth-status note.
- **Identifier resolution drift.** Refs like `components/complex-styled-button[icon]` can rot silently when files move or rename.
  *Mitigation:* Same convention-only posture as v1; reviewer attention. Future v3 tooling can lint without format changes.
- **Reviewer confusion during transition.** During Proposit migration, reviewers see both layouts.
  *Mitigation:* `docs/file-locations.md` opens with a clear "the parallel `docs/capabilities/` tree is canonical; co-located files are legacy and being migrated out" note.
- **Sidecar overuse.** Authors may reach for sidecars when prose would suffice.
  *Mitigation:* `docs/sidecars.md` opens with the two-test rule (entries are enumerable AND referenced from other capabilities); says "prose first; sidecar only when both tests pass."
- **`.config.yaml` becoming a kitchen sink.** Projects may try to redefine status vocabulary or grammar in config.
  *Mitigation:* `docs/trackers.md` explicitly lists what does *not* belong in `.config.yaml`; the file is for project-shaped details only.

---

## 10. Open questions

None at brainstorm sign-off. The implementation plan (writing-plans phase) should resolve these as it goes:

- Final wording for each rewritten doc file, especially `docs/format.md` (the densest one).
- Whether the new generic exemplars live alongside the existing Proposit-style exemplars or in a separate `docs/exemplars/generic/` subfolder.
- Exact wording of the per-repo CLAUDE.md `Documentation Sync` entry update for v2 (the glob now points at `docs/capabilities/**/*.md` instead of `**/capabilities.md`).
- Whether `docs/format.md` should include a small reference grammar (EBNF-style) for the cross-reference identifier syntax in addition to the prose explanation.

---

## 11. References

- Prior art survey (in the brainstorming session): Cucumber/Gherkin, SpecFlow, Concordion, Backstage TechDocs, Stoplight Elements, ADRs (Nygard/MADR), arc42, C4 model, Aha! capability mapping, ReqIF, OpenAPI `x-*` extensions, JSON Schema `$ref`, Linear/GitHub Issues markdown linking.
- v1 skill files (current state, replaced by this spec): `skills/capabilities-sdlc/SKILL.md` and the `docs/` siblings.
- Inbox archive of the originating proposal: `docs/inbox/.archive/proposal.md`.
