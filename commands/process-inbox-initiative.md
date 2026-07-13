---
description: Workspace-coordinator workflow for processing an inbox request as a multi-repository initiative: capabilities first, then one durable agent per affected repository through research, review, implementation, and integration.
---

# Process Inbox — Initiative

Coordinate a multi-repository request as one initiative. Establish intended capabilities first, then assign exactly one durable top-level agent to each affected repository. Each repository agent owns local research, review, implementation, and integration support and may use its own subagents when the current agent environment supports them.

Top-level agent budget: **one spawned agent per affected repository**. Coordinate repository agents in parallel when useful, but do not create separate top-level researcher, reviewer, architect, or developer agents for the same repository.

## 0. Confirm the workspace role

Use this command only from the workspace-coordinator role declared by the host workspace. Determine that role from `AGENTS.md`, `CLAUDE.md`, a workspace registry, or explicit user direction.

If operating inside a child repository without workspace authority, stop and use `/skill-cefailures:process-inbox` instead. Do not infer coordinator authority from a directory name alone.

Before continuing, discover the host's conventions for:

- member repositories and their locations;
- capability roots and any shared product layer;
- branch, commit, and handoff policy;
- planning/spec locations and review requirements;
- initiative ledgers or per-repository briefings; and
- available agent coordination mechanisms.

Treat undeclared facilities as absent; do not create a product layer, ledger, broker, or planning hierarchy merely because this command mentions one.

## 1. Read and route the inbox request

Follow steps 1–5 of `/skill-cefailures:process-inbox`: verify the inbox, enumerate candidates, choose one, locate the request document, then read it with bundled artifacts.

Do not archive yet. For an initiative, the durable initial artifact is the overview spec or equivalent host-declared planning artifact.

## 2. Capabilities-first pass

Use `capabilities-sdlc` and the host project's declared capability layout. For each requested behavior:

- Cross-check repo-local capability documents in affected repositories.
- If the workspace declares a shared product layer, cross-check it through the authorized coordinator role.
- Add an absent desired capability as `Missing` using the skill's current taxonomy.
- When an existing capability covers only part of the request, keep it `Missing` and state what works and what remains. Mark it `Supported` only when the documented behavior works in full.
- After a spec exists, add its reference according to the host project's reference conventions.

Commit capability changes separately from implementation when the host repository policy expects commits. Follow each repository's target branch and handoff policy; never assume `main` or direct commits are allowed.

Because the workspace coordinator may lack write authority in child repositories, dispatch the single durable repository agent as soon as an affected repository is known. Its first assignment may be the repo-local capability update. Give it the relevant request context, local policy, and instruction to remain available for later phases.

If the host declares no capability documentation, record the intended behavior in the overview spec and continue. Do not introduce a capability system without user approval.

## 3. Create the overview artifact, then archive

Write the overview spec or equivalent artifact at the location declared by the host workspace. When capability documentation is in use, open it with `## Capability changes`, then cover scope, repository ownership, dependency ordering, and integration risks.

If the workspace maintains an initiative ledger or per-repository status files, seed them now. If it does not, track milestones in the overview artifact.

Once the durable artifact exists, archive the inbox source using `/skill-cefailures:process-inbox` step 6. Move a loose file or the entire request bundle into `docs/inbox/.archive/`, preserving collision safeguards.

## 4. Research and architecture

- Determine affected repositories from the request, capability cross-check, workspace registry, and repository evidence.
- Ensure exactly one top-level repository agent is active for each affected repository. Reuse any agent dispatched during the capability pass.
- Have repository agents investigate local questions and return a synthesis with file references, constraints, tests, and risks. They may use subagents only within their repository boundary and only when supported.
- Keep cross-repository architecture and dependency ordering with the workspace coordinator.
- Author repository-scoped specs using the host's installed planning workflow. If none is declared, use concise Markdown specs directly.
- Stop at specification level during this phase; do not mix unapproved implementation into architecture research.

## 5. Review gate

Send each repository spec to its existing repository agent for the review process required by that repository. The agent may coordinate local subreviews, but do not spawn a separate top-level reviewer for the repository.

Resolve actionable findings, then obtain any human approval required by the host workspace before implementation.

## 6. Implementation

After approval, have each durable repository agent plan and implement its repository's slices under local instructions. Preserve test, debugging, documentation-sync, commit, and verification requirements from that repository.

Reconcile the initial `Missing` capability entry as work lands: add the final spec reference and change status only when implementation evidence supports it. Do not recreate a duplicate entry.

Repository agents may manage local worktrees or internal subagents when their environment and repository policy permit it. The workspace coordinator continues to communicate through the coordination mechanism available in the current agent platform.

## 7. Integration

Create a cross-repository merge or landing plan. Each repository agent consolidates its local work into the branch or pull request shape required by that repository. A multi-repository initiative normally produces one integration branch or pull request per repository, not one cross-repository Git branch.

Track total initiative state in the overview artifact and, when present, the workspace ledger.

## Throughout: briefings and milestones

If the workspace uses per-repository briefings, update each briefing before asking the repository agent to begin spec or implementation work. Otherwise, send the same information through the available coordination channel and keep the overview artifact authoritative.

Record these milestones in the host's chosen tracking surface:

- overview artifact created;
- capability intent recorded;
- each repository spec reviewed and approved;
- each implementation slice landed; and
- blockers raised or cleared.

When an optional facility is unavailable, use the documented fallback and continue. Pause only when authority, scope, or a material product decision cannot be inferred safely.
