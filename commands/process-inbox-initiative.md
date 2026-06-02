---
description: Orchestrator-only. Process an org-root inbox doc as a multi-repo initiative — capabilities-first, then one repo agent per affected repo coordinates research, review, implementation, and integration. Builds on process-inbox.
---

# Process Inbox — Initiative

The workspace-root orchestrator drives multi-repo feature work as a single
**initiative**: capabilities are marked first, then the orchestrator spawns exactly
one durable agent per affected repository. Each repo agent owns repo-local research,
spec feedback, implementation, code review, and integration support for that repo,
using subagents for research and code review rather than standing top-level
researcher or reviewer agents. This command codifies that recipe so it no longer has
to be pasted into each inbox document by hand.

Top-level agent budget: **one spawned agent per affected repo**. The orchestrator may
coordinate those repo agents in parallel, but it must not spawn separate top-level
researcher, reviewer, architect, or developer agents for the same repository.

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
- **Early repo-agent dispatch:** because the orchestrator does not commit into child
  repos, spawn the single durable repo agent for each affected repo as soon as that
  repo is known. Its first job is to commit that repo's `capabilities.md` (**Status:
  Missing**, spec reference pending) as a standalone commit on `main`. This precedes
  the overview spec and the per-repo briefing, so give the agent the full single-commit
  instruction inline and tell it to remain available for the rest of the initiative.
  It still honors the child-repo "commit-to-`main` handoff" convention from the org
  `CLAUDE.md`.

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
- Ensure exactly one top-level repo agent is running for each affected repo. If step 2
  already dispatched that repo agent for the capabilities commit, reuse it; do not
  spawn a researcher, reviewer, architect, or developer as a separate top-level agent
  for that repo.
- The orchestrator acts as the cross-repo architect:
  - sends repo-scoped research questions to the relevant repo agent via `SendMessage`;
  - instructs each repo agent to use research subagents for read-only investigation
    where that helps, then return a synthesized answer with file references,
    constraints, and risks;
  - determines the implementation order and the inter-repo dependency DAG;
  - authors per-slice **implementation specs** (using `writing-plans` for
    spec-authorship guidance; `brainstorming` only if the scope is ill-defined).
    Spec-level only — **no implementation plans, no code** during this phase.

## 5. Spec review gate (per spec)

- After each spec is finished, send it to the relevant repo agent for review. Do not
  spawn a separate top-level reviewer.
- The repo agent performs the review using subagents: run the repo's expected
  dual-review strategy inside the agent boundary (for example, a non-Claude model pass
  plus a Claude subagent pass, synthesized) and report actionable findings back to the
  orchestrator.
- Then the **user does the final human check** on the spec before any implementation
  begins.

## 6. Implementation

- After spec review and the human check are complete, the existing repo agent
  implements the repo's approved slices under the superpowers plugin. TDD,
  systematic-debugging, and verification-before-completion are baseline.
- Each repo agent runs `writing-plans` for its own repo work (spec → plan), then
  implements. It may coordinate internal subagents only within its own session; the
  orchestrator still has exactly one top-level agent per repo.
- Cross-repo parallelism is one repo agent per affected repo. If a single repo has
  independent implementation slices, the repo agent manages that repo's local
  worktrees and sequencing (`using-git-worktrees` / `dispatching-parallel-agents`) and
  reports progress through the same repo-agent channel.
- The repo agent's **first implementation-branch commit** updates that repo's
  `capabilities.md` — **reconciling against** the step-2 caps commit already present on
  the branch base (filling in the spec reference, flipping status as work lands), not
  re-creating the entry. Its briefing must note that the step-2 commit already
  happened.

## 7. Integration

- The orchestrator authors the cross-repo **merge plan**. Each repo agent combines any
  local worktrees *within its repo* into that repo's single integration branch for the
  initiative. The orchestrator coordinates the per-repo branch/PR handoff.
- **On "a single branch":** git worktrees are per-repo, so "a single branch
  representing the totality of all work" is realized as **one integration branch per
  affected repo**. Cross-repo totality is tracked by the overview spec and the
  initiatives ledger, not by a single cross-repo branch.

## Throughout: repo-agent briefings + ledger

- Per-repo briefings (`<repo>/docs/superpowers/briefings/<initiative>-<repo>-agenda.md`)
  are the entry points repo agents read first once the overview spec exists. Early
  caps-only work is the only briefing-less repo-agent task.
- Briefings must name the single-agent constraint explicitly: the repo agent owns
  research, review, implementation, and integration support for that repository, and
  uses subagents for research and code review instead of requesting separate
  top-level agents.
- Update the initiatives ledger at each milestone: overview spec written, each spec
  reviewed/approved, each slice merged, blockers raised or cleared.
