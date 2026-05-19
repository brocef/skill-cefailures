# Follow-ups

Standing log of deferred code-related follow-up items. New entries are prepended; completed items are annotated in place (strikethrough + completion date), not deleted.

# Skill-to-command migration — wave 2
Commit range: 2b074d0-1ac5c30
Branch name: main
Added on: 2026-05-19

## Follow-up Items
- ~~Convert `broker` skill to 100% command-driven. User intent: remove `skills/broker/` entirely (SKILL.md was already "explicit invocation only"); create namespaced commands like `/skill-cefailures:broker:setup`, `/skill-cefailures:broker:mode` (replacing `/broker-mode`), `/skill-cefailures:broker:send`, `/skill-cefailures:broker:read`, `/skill-cefailures:broker:doctor`. Decide whether the seven existing `skills/broker/docs/*.md` files move into command bodies, into a top-level `docs/broker/` reference tree, or stay where they are and get path-referenced from commands. Update `plugin.json` keywords and README accordingly.~~ (completed 2026-05-19; final shape: 5 commands under `commands/broker/`; `skills/broker/docs/` left in place and read by commands via path; `SKILL.md` pared to a namespace stub rather than deleted, per user preference)
- ~~Refactor `documentation-sync` skill (currently 339-line SKILL.md). User-requested splits to consider: move the `## Release Notes & Changelogs` section to a sub-document; extract the `## Version Management` "cut a version" workflow into a `/skill-cefailures:documentation-sync:cut-version` command (offer-trigger stays in SKILL.md, execution recipe moves to command body); audit the rest of the SKILL.md for further sub-document candidates.~~ (completed 2026-05-19; SKILL.md trimmed from 333 → 91 lines. Created `docs/release-notes-and-changelogs.md` and `docs/follow-ups.md` sub-docs; the `## Follow-ups` section was the audit finding from bullet 3. Created `/skill-cefailures:documentation-sync:cut-version` with the bump-rotate-commit-tag recipe + bump-size guidance + version-cut common mistakes; the "When to offer a version cut" trigger remains in SKILL.md.)

## Additional Notes
- Wave 1 handled: brain-review, brain-claude-md, doc-sync setup, permissions-auditor install, permissions-auditor analyze. All five became commands; `permissions-auditor` skill removed entirely.
- Wave 2 handled: broker conversion (5 commands + SKILL.md stub) and documentation-sync deeper refactor (2 sub-docs + 1 new command + SKILL.md slim).
- Naming convention going forward: commands grouped by source skill via subdirectory (`commands/<skill>/<action>.md`), surfaced by Claude Code as `/skill-cefailures:<skill>:<action>`.
