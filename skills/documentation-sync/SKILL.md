---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project's CLAUDE.md has a Documentation Sync section listing files and triggers. Use after completing any development work to update release notes and changelogs.
---

# Documentation Sync

After completing code changes, check the project's `CLAUDE.md` for a `## Documentation Sync` section and evaluate each listed file's trigger before reporting the task complete. If the section is missing, ask the user if they'd like to add one (see `docs/setup.md`).

| Doc | Scope |
|-----|-------|
| `docs/section-format.md` | What the Documentation Sync section looks like in CLAUDE.md and how entries are structured |
| `docs/evaluating-triggers.md` | Trigger definitions and how to assess code changes against them |
| `docs/release-notes.md` | Per-version file structure, `upcoming.md` workflow, changelog entry format, version cross-checks |
| `docs/setup.md` | Creating a Documentation Sync section from scratch |
