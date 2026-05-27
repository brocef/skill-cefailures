---
description: Orchestrator-only. Process an org-root inbox doc as a multi-repo initiative — capabilities-first, then research → architect specs → dual review → parallel dev → integration. Builds on process-inbox.
---

# Process Inbox — Initiative

The workspace-root orchestrator drives multi-repo feature work as a single
**initiative**: capabilities are marked first, an architect plans the ordering and
authors per-slice specs (outsourcing research to per-repo researchers), each spec is
dual-reviewed and human-checked, then developers implement in parallel worktrees and
the work is integrated per repo. This command codifies that recipe so it no longer
has to be pasted into each inbox document by hand.

## 0. Scope guard

This command is for the **workspace-root orchestrator only**. If you are a per-repo
agent (spawned inside `proposit-core/`, `proposit-shared/`, `proposit-server/`,
`proposit-mobile/`, etc.), stop — use `/skill-cefailures:process-inbox` instead.

## 1. Read & route the inbox doc

Do steps 1–5 of `/skill-cefailures:process-inbox` (verify inbox exists → enumerate
candidates → pick a candidate → locate the request doc inside a bundle → read it).

Do **not** archive yet. `process-inbox` archives once a request has been "ingested
into an initial artifact"; for an initiative that durable artifact is the overview
spec, so archiving is deferred to step 3.

## 2. Capabilities-first pass

Driven by the `capabilities-sdlc` skill. The inbox doc stays the live source of truth
through this step (it is not archived until step 3). For each requested item:

- Cross-check the relevant per-repo `capabilities.md` in the affected repos **and**
  the product-layer `docs/capabilities/<area>.md` at the org root.
- The status taxonomy is exactly **Supported | Missing | Omitted** — there is no
  "Partial" status (see `capabilities-sdlc`, `docs/statuses.md`).
- **Capability not present** → add it with **Status: Missing**. Once a spec exists,
  add a reference to the planning doc in that capability's section, so the file tracks
  *how* the capability will be added.
- **Capability present but missing some requested behaviors** → still **Status:
  Missing**, with the body noting which behaviors exist and which don't. A
  **Supported** status requires *all* requested behaviors.

Commit the capabilities changes in their own commit(s), separate from any
implementation:

- The orchestrator commits the **product-layer** `docs/capabilities/<area>.md` changes
  at the org root in their own commit (this is in orchestrator scope — the org-root
  `proposit-orchestration` repo).
- **Early caps-only dispatch:** because the orchestrator does not commit into child
  repos, dispatch a lightweight per-repo agent into each affected repo to commit that
  repo's `capabilities.md` (**Status: Missing**, spec reference pending) as a
  standalone commit on `main`, before the architect runs. This is a deliberately
  briefing-less micro-dispatch — it precedes the overview spec and the per-repo
  briefings, so there is no briefing for it to read; give it the full single-commit
  instruction inline. It still honors the child-repo "commit-to-`main` handoff"
  convention from the org `CLAUDE.md`.

## 3. Overview spec + ledger, then archive

- Write the overview spec to
  `docs/superpowers/specs/YYYY-MM-DD-<initiative>-overview.md`. Per the planning gate,
  it **opens with a `## Capability changes` section** as its first content section,
  then covers the full scope, the inter-repo dependency DAG, and ordering
  recommendations.
- Seed the initiatives ledger: an entry in `docs/initiatives/INDEX.md` plus the
  relevant per-repo `docs/initiatives/{repo}.md` files.
- **Now archive the inbox source** (`process-inbox` step 6): loose file → move the
  file; folder bundle → move the whole folder; create `docs/inbox/.archive/` if
  needed; append a timestamp suffix on a name collision rather than overwriting. The
  overview spec is now the durable artifact; the archived source is no longer
  load-bearing.

## 4. Research + architecture

- Determine the affected repos from the capabilities cross-check (step 2).
- **The orchestrator spawns** one **code researcher per affected repo** (read-only, on
  standby) and **the code architect**. The architect does *not* spawn agents — it only
  queries the standing researchers via `SendMessage`.
  - If an affected repo has no `<repo>-researcher.md` briefing yet (e.g.
    `proposit-mobile` is not yet formalized — see the org `CLAUDE.md` "Team agents and
    review cadence" section), author one per the standing
    `docs/agents/<repo>-researcher.md` pattern before dispatch, or surface the gap to
    the user.
- The architect then:
  - outsources all research to the researchers via `SendMessage`;
  - determines the implementation order and the inter-repo dependency DAG;
  - authors per-slice **implementation specs** (using `writing-plans` for
    spec-authorship guidance; `brainstorming` only if the scope is ill-defined).
    Spec-level only — **no plans, no code**. The architect is read + spec-write only.

## 5. Spec review gate (per spec)

- After each spec is finished, spawn the per-repo **reviewer** to **dual-review** it.
  The reviewer briefings (`docs/agents/<repo>-reviewer.md`) define the dual-review
  strategy (a non-Claude model pass plus a Claude subagent pass, synthesized).
- Then the **user does the final human check** on the spec before any implementation
  begins.

## 6. Implementation

- After spec review is complete, spawn **developer agents** (under the superpowers
  plugin — TDD, systematic-debugging, and verification-before-completion are baseline).
- Each developer runs `writing-plans` for its own task (spec → plan), then implements.
- If parallel work is possible: one developer per parallel task, each in a **distinct
  worktree** (`using-git-worktrees` / `dispatching-parallel-agents`).
- Each developer's **first commit** on its branch updates that repo's
  `capabilities.md` — **reconciling against** the step-2 caps commit already present on
  the branch base (filling in the spec reference, flipping status as work lands), not
  re-creating the entry. The dev's briefing must note that the step-2 commit already
  happened.

## 7. Integration

- The architect authors the **merge plan** and combines the parallel worktrees
  *within each affected repo* into that repo's single integration branch for the
  initiative. The orchestrator coordinates worktree lifecycle and the per-repo
  branch/PR.
- **On "a single branch":** git worktrees are per-repo, so "a single branch
  representing the totality of all work" is realized as **one integration branch per
  affected repo**. Cross-repo totality is tracked by the overview spec and the
  initiatives ledger, not by a single cross-repo branch. (The architect briefing's
  "one integration branch" is per-repo; this command makes that explicit for the
  multi-repo case.)

## Throughout: briefings + ledger

- Per-repo briefings (`<repo>/docs/superpowers/briefings/<initiative>-<repo>-agenda.md`)
  are the entry points researchers and developers read first.
- Update the initiatives ledger at each milestone: overview spec written, each spec
  reviewed/approved, each slice merged, blockers raised or cleared.
