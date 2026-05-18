# The contradiction-detection rule

## The rule

Before completing a code change that affects user-facing behavior, check whether the change contradicts any existing `capabilities.md` entry — by status, by described scope, or by listed conditions. If it does:

1. **Surface the contradiction to the user.** Name the file, the capability heading, the current wording or status, and the specific way the proposed change conflicts with it.
2. **Ask which side moves.** Either update the `capabilities.md` to match the new behavior, or revise the change to fit the existing documented capability.
3. **Do not silently update the `capabilities.md`.** Never reconcile the contradiction by rewriting the capability file on the user's behalf without explicit direction.

The check runs at the same moment the change is being made — not at session end, not at PR review. The developer making the change is in the best position to spot the conflict, and surfacing it then forces an intentional decision before the diff is committed.

## When the rule applies

Any code change that affects user-facing behavior, including:

- A route or screen's interactive surface (forms, buttons, navigation targets, displayed fields).
- An API endpoint's contract (accepted inputs, returned shape, authorization requirements, error cases).
- A feature flow's preconditions, postconditions, or branch points.

The trigger is the same one the `**/capabilities.md` Documentation Sync entry uses — a code change in the same directory or subtree as a capability file. The difference is timing: Documentation Sync evaluates *after* the change is staged; contradiction detection evaluates *while* the change is being designed or written.

The rule does not apply to changes that don't touch user-facing behavior: internal refactors, dependency bumps, test-only changes, comment-only changes, build-tooling changes.

## Contradiction shapes

Three common shapes. The list is illustrative, not exhaustive — any way a change conflicts with what an existing capability entry asserts counts.

### Status-flip contradiction

The change introduces behavior that an existing entry says is `Missing` or `Omitted`, or removes behavior an entry says is `Supported`.

Examples:

- Entry says `**Status:** Missing` for "Reset password (email)" — the proposed change implements the email reset flow. The entry's status is now wrong.
- Entry says `**Status:** Omitted` for "Magic-link sign-in" with a body explaining the OAuth-only decision — the proposed change adds a magic-link option. The entry's omission rationale is now wrong.
- Entry says `**Status:** Supported` for "Edit argument title after publish" — the proposed change locks the title field once published. The entry no longer describes reality.

### Scope contradiction

The change broadens or narrows the user roles, modes, or conditions under which the capability fires.

Examples:

- Entry says the action is owner-only — the proposed change makes it editor-accessible as well. The role scope has widened.
- Entry says the action is available to all signed-in users — the proposed change restricts it to verified-email accounts. The role scope has narrowed.
- Entry describes a single mode (e.g., "draft arguments") — the proposed change fires the same action in a second mode (e.g., "published arguments" too). The mode scope has widened.

### Condition contradiction

The change alters `When …:` conditions or other body-level enumerations the entry lists.

Examples:

- Entry says "when the argument is published" — the proposed change makes the capability fire on drafts too.
- Entry enumerates three accepted input formats — the proposed change adds a fourth (or removes one).
- Entry says the side effect (email, notification, audit log) fires only on success — the proposed change makes it fire on failure paths too.

## How to surface the contradiction

A simple format works:

> The change at `<path>` contradicts `<capabilities.md path>#<heading-slug>`. The entry currently says `<short quote or status>`; the change would make `<one-line summary of new behavior>`. Should the entry be updated to match the new behavior, or should the change be revised to fit the existing entry?

Wait for the answer before completing the change. The two valid resolutions are:

- **Update the capability file** — the documented intent was wrong or out of date; the new behavior is correct. The agent then updates the `capabilities.md` (and, if it changes product-level intent, surfaces that to the orchestrator per `docs/product-layer-coordination.md`).
- **Revise the code change** — the documented intent was right; the proposed behavior was incorrect or out of scope. The agent then changes the implementation to match the entry.

A third path — "the entry is right *and* the new behavior is right because they describe different capabilities" — is also possible. In that case, the resolution is to add a new capability heading to the file rather than mutate the existing one. Surfacing the contradiction first is still required, because the disambiguation is itself a user decision.

## What this rule is *not*

- **Not a substitute for the planning gate.** A spec or briefing for the change should already declare the capability intent via its `## Capability changes` section (see `docs/planning-gate.md`). Contradiction detection is the last-mile check when implementation reveals a conflict the plan didn't anticipate.
- **Not a substitute for Documentation Sync.** Contradiction detection runs *during* the change; the `**/capabilities.md` Documentation Sync trigger evaluates *after* the change is staged. Both can fire on the same diff.
- **Not a license to silently update.** Even an "obvious" reconciliation — the entry is plainly stale, the new behavior is plainly correct — requires asking. The principle is that capability files describe *intended* state and a unilateral rewrite removes the user's chance to push back on the intent.
