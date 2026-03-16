---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project's CLAUDE.md has a Documentation Sync section listing files and triggers. Use after completing any development work to update release notes and changelogs.
---

# Documentation Sync

After completing code changes, check the project's `CLAUDE.md` for a `## Documentation Sync` section. If present, evaluate each listed file's trigger to decide what documentation to update before considering the task done.

## When to Use

- After making ANY code change, before reporting task completion
- When a project's CLAUDE.md contains a `## Documentation Sync` section

When NOT to use:
- Changes are limited to documentation files only (no code was changed)

If the `## Documentation Sync` section is **missing** from CLAUDE.md, ask the user if they'd like to add one. If yes, see the Setup sub-task below.

## Sub-Tasks

Read the relevant doc based on your task:

- **Section Format** — `docs/section-format.md` — What the Documentation Sync section looks like in a CLAUDE.md and how entries are structured.
- **Evaluating Triggers** — `docs/evaluating-triggers.md` — Trigger definitions, how to assess code changes against triggers, and when to update or skip a file.
- **Release Notes & Changelogs** — `docs/release-notes.md` — Per-version file structure, `upcoming.md` working files, changelog entry format (commit hash ranges), version cross-checks, recommended Documentation Sync entries, and migrating existing projects.
- **Setup** — `docs/setup.md` — Creating a Documentation Sync section from scratch when a project doesn't have one.
