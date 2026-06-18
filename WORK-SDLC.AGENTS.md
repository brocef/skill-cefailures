# WORK-SDLC — agent working guide

Working guidelines for the **Work SDLC** sub-project: the recursive, storage-abstracted work-tracking system (the `work` CLI + its skills, replacing the ad-hoc inbox → specs → `FOLLOWUPS.md` flow). For general repo conventions, follow `AGENTS.md`; this file adds only what is specific to this sub-project.

**Design source of truth:** [`docs/superpowers/specs/2026-06-18-work-sdlc-design.md`](docs/superpowers/specs/2026-06-18-work-sdlc-design.md). Read it before changing the model. If a change diverges from the spec, update the spec in the same change — never let code and design drift.

## Prime directive: the abstraction litmus test

The Work SDLC ships a filesystem-native default, but the **model is storage-abstracted** so it can run against an external tracker (e.g. Jira) where one is already in use. That portability is the whole reason the system is viable at enterprise scale — do not trade it away for filesystem cleverness. Before adding or changing any operation, apply this test:

> **"Could a non-filesystem store implement this operation, even if less elegantly?"**
> - **Yes** → it belongs in the model / the abstract store interface.
> - **No** — it only works as a filesystem trick with no abstract analog → push it into the filesystem adapter as a private detail, or redesign it.

## Abstract spine, filesystem leverage

Express behavior in the abstract vocabulary — **item · status · transition · stable ID · reference · node relation · query · body/fields/attachments** — and let the filesystem *realize* it. Filesystem superpowers are bonuses layered on top, never load-bearing assumptions of the model.

- **Leverage freely (bonuses):** work-docs co-located with code (one repo / worktree / PR / diff); one atomic commit carrying code change + capability status flip + work-item transition; grep/diff/PR-review legibility; atomic `mv` as transition.
- **Keep out of the model (no abstract analog):**
  - Reconstructing current state from git history — *state is the status; git is archive.*
  - Globbing the work folder as an open namespace — *bound it: body + named fields + named attachments.*
  - Hard-coded paths in references/links — *use stable IDs; resolve through the store.*
  - Parent/child as literal directory ancestry outside the node-resolution layer — *express the relation abstractly; the FS adapter derives it from nesting.*
  - Worktrees and `rg`/`find` queries — *filesystem-adapter local details, not store-interface operations.*

## Implementation rules

- `WorkStore` is the interface the CLI and skills depend on. Ship the filesystem adapter (`FsWorkStore`) only; keep `JiraWorkStore` possible but unbuilt. Never add an interface method that only `FsWorkStore` could honor (run the litmus test first).
- Capability tracking is **part of** this system, not a separate skill — see the design spec's capabilities section (A.7). Don't reintroduce a standalone `capabilities-sdlc` dependency.
- Follow the repo's existing patterns: the `Backend` ABC in `create_skill.py` is the model for `WorkStore`; Python with type hints; pytest over `tmp_path` git repos.
