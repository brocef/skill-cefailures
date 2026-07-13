# The planning gate

## The rule

**Every feature brainstorm, spec, plan, or briefing opens with a `## Capability changes` section as its first content section.** Architecture, implementation, and test discussion happens *after* the capability changes are described.

This applies to:

- Brainstorms in any repo that adopts this skill.
- Specs under `docs/superpowers/specs/`.
- Plans under `docs/superpowers/plans/`.
- Per-repo briefings under `<repo>/docs/superpowers/briefings/`.
- Cross-repo overview specs at the workspace root.

## What goes in the section

Plain prose, no specific schema. Cover three buckets:

1. **New capabilities** — which `capabilities.md` they will be added to (or which file will be newly created), with proposed statuses.
2. **Updated capabilities** — path + capability name, what is changing about the body or status. A status flip from `Missing` to `Supported` counts.
3. **Deleted capabilities** — what's being removed and why. A `Supported` → `Omitted` flip is a deletion of intent.

Example:

```markdown
## Capability changes

- **New:** `apps/web/src/app/account-recovery/capabilities.md` — declares "Request account-recovery email" as `Missing` because this change scaffolds the route while delivery remains follow-up work.
- **Updated:** `apps/mobile/src/screens/LoginScreen/capabilities.md#sign-in-with-an-identity-provider` — body updated to describe platform-specific behavior.
- **Updated:** `docs/capabilities/auth.md#recover-account` — flips from `Missing` to `Supported` after the implementation lands.
```

The section is the *first* content section of the document. It precedes architecture, design alternatives, implementation tasks, and tests. It can be brief — the point is to force the planner to articulate the intent change before getting absorbed in implementation.

## Bug fixes

The gate applies only when the bug fix changes the *intended* capability:

- **Pure regression fix** (capability file says `Supported`, behavior previously worked, behavior is now broken, fix restores previous behavior): no gate. The intent didn't change; the implementation regressed and is being repaired.
- **Discovery fix** (capability file says `Supported`, behavior never actually worked): **gate applies**. The documented intent is itself in question. The fix may need to update the capability description, the status, or both.
- **Capability change disguised as a bug fix** (the user reports a bug, the team decides the right answer is to change what's intended): gate applies. The capability description must be updated.

When in doubt, run the gate. The cost of one extra `## Capability changes` section is small; the cost of shipping intent changes without documenting them is large.

## Why this gate exists

Capabilities files are only as useful as their accuracy. If features ship without updating the documents, they drift toward fiction. The gate is the simplest mechanism that prevents drift: every plan touches the file, so every PR's reviewer can see the intent diff before reading the code diff.

## Enforcement

This skill is surfaced to agents whose context matches the trigger description — including planning, brainstorming, or specifying user-facing changes. When an agent invokes the skill, the gate is stated prominently. Beyond that, enforcement is convention:

1. The skill document.
2. The host workspace's `AGENTS.md` or `CLAUDE.md` requires that relevant plans open with `## Capability changes`.
3. Each adopting repository carries a one-line note: *"Plans and specs in this repo open with a `## Capability changes` section. The `capabilities-sdlc` skill defines the format."*

There is no automated lint or CI check; reviewer attention is the backstop.
