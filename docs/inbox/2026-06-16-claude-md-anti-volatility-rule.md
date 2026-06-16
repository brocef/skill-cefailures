# Change request: add a stability / anti-volatility rule to the `claude-md` command

**Target skill/command:** `commands/brain-style/claude-md.md` (the `/skill-cefailures:brain-style:claude-md` review-and-author command).

## Problem

When auditing the Proposit workspace's `CLAUDE.md`/`AGENTS.md` files, several had drifted badly out of date:

- `proposit-mobile` described a bare "sub-project 1A scaffold that renders 'Proposit'" while the app had actually shipped auth, navigation, a read path, reviews, and deep-links.
- The workspace-root and `proposit-server` files carried dependency pins that were several minor/major versions stale (e.g. `@proposit/proposit-core ^0.12.3` when the real pin was `^1.11.0`).
- `proposit-server` carried deep per-endpoint and per-env-var prose that referenced a deleted spec file and renamed routes.

The common failure mode wasn't "nobody maintained the docs" — it was that the docs **inlined volatile facts**: things that change on an ordinary development cadence and therefore go stale almost immediately. A context file should be **stable** — it should rarely need editing, because most ordinary PRs (a dep bump, a file move, a version cut, a feature shipping) should not invalidate any line in it.

## Root cause (skill gap)

`commands/brain-style/claude-md.md` already teaches the minimal-routing principle and an "Inline vs. Route" decision. But the **"Route when"** triggers are framed around *where the fact is defined* ("defined in another file") and *how broadly it applies* ("narrow subset of tasks"). Neither axis captures **volatility** — *how often the fact changes* — which is the axis that actually caused the drift. There is also no explicit list of the high-churn content types that should never be inlined.

## Proposed fix

Add **volatility** as a first-class reason to route content out, plus a concrete banned-content list. Suggested additions:

### 1. New "Route when" bullet

Under **Route when:** add:

> - **It is volatile** — it changes on an ordinary development cadence (a dependency bump, a refactor, a version cut, a feature shipping). Inline only facts that survive routine PRs; route everything that a normal change would invalidate to its canonical source.

### 2. New rule section: "Keep it stable (anti-volatility)"

> A `CLAUDE.md` should rarely need editing. Before inlining a fact, ask: **"Would a routine PR make this line wrong?"** If yes, route it to where it's already maintained instead of copying it in. Specifically, do **not** inline:
>
> | Volatile content | Route to / do instead |
> |---|---|
> | Exact dependency version pins (`^0.9.0`, `~54.0.34`, `next 16.2.2`) | Name the framework/major identity only if useful (e.g. "Expo SDK 54", "Next.js 16"); the exact pins live in `package.json`. |
> | A "Status" / "current phase" / "what's shipped so far" section | Delete it — the repo's current state is in git history and the code, and a status line is stale the moment the next PR merges. |
> | Deep file paths and line numbers that move on refactor (`src/app/view/[id]/[v]/contexts/...`) | Reference a stable directory or an exported symbol/function name, not a churning path. |
> | Long operational or reference blocks only some tasks need (release/App-Store checklists, per-endpoint API essays, per-env-var mechanics) | Move to a dedicated doc (e.g. a runbook, an architecture doc) and leave a keyword-rich routing pointer. |

### 3. New "Common Mistakes" rows

| Mistake | Fix |
|---|---|
| Inlining exact dependency versions | They go stale on the next bump — name the major identity if needed, route exact pins to `package.json` |
| A "Status"/"current phase" section | Delete — inherently stale; state lives in git + code |
| Deep file paths / line numbers in prose | Reference stable dirs or exported symbols instead |

## Impact on consumers

- The `claude-md` command produces smaller, more durable context files and gives the reviewer a crisp test ("would a routine PR make this line wrong?") for what to cut.
- The Proposit `AGENTS.md` files were just refactored under exactly these rules (volatile pins removed, mobile "Status" section deleted, server's release/compliance detail routed to a runbook). They should pass the new check; this CR back-fills the rule that the refactor followed so future authoring is consistent.

## Test cases (review-time checks the updated command should catch)

1. A `CLAUDE.md` line stating `"@proposit/shared@^0.9.0"` → flagged; replaced with a `package.json` pointer.
2. A `## Status` / `## Current phase` section → flagged for deletion.
3. A 50-line App-Store / release checklist inlined in `CLAUDE.md` → flagged; routed to a runbook with a pointer left behind.
4. A prose reference to `src/app/view/[argumentId]/[version]/contexts/arg-data-context/...` → flagged; replaced with a stable directory or symbol reference.
5. A file that survives the "would a routine PR make this wrong?" test on every line → passes.

## Notes

- This composes with, and does not replace, the existing minimal-routing principle and required-sections checklist — it adds the *volatility* axis those sections were missing.
- If any of the above is better expressed as a tweak to `documentation-sync` (so a stale pin trips a sync trigger) rather than `claude-md`, that's a reasonable alternative placement — but the authoring-time guidance belongs in the `claude-md` command.
