# Follow-ups

Standing log of deferred code-related follow-up items. New entries are prepended; completed items are annotated in place (strikethrough + completion date), not deleted.

# Skill-to-command migration — wave 2
Commit range: 2b074d0-HEAD
Branch name: main
Added on: 2026-05-19

## Follow-up Items
- ~~Convert `broker` skill to 100% command-driven. User intent: remove `skills/broker/` entirely (SKILL.md was already "explicit invocation only"); create namespaced commands like `/skill-cefailures:broker:setup`, `/skill-cefailures:broker:mode` (replacing `/broker-mode`), `/skill-cefailures:broker:send`, `/skill-cefailures:broker:read`, `/skill-cefailures:broker:doctor`. Decide whether the seven existing `skills/broker/docs/*.md` files move into command bodies, into a top-level `docs/broker/` reference tree, or stay where they are and get path-referenced from commands. Update `plugin.json` keywords and README accordingly.~~ (completed 2026-05-19; final shape: 5 commands under `commands/broker/`; `skills/broker/docs/` left in place and read by commands via path; `SKILL.md` pared to a namespace stub rather than deleted, per user preference)
- Refactor `documentation-sync` skill (currently 339-line SKILL.md). User-requested splits to consider:
  - Move the `## Release Notes & Changelogs` section to a sub-document — only needed when the agent is touching release notes or changelogs.
  - Extract the `## Version Management` "cut a version" workflow into a `/skill-cefailures:documentation-sync:cut-version` command. The "offer to bump" trigger stays in SKILL.md; the execution recipe (bump, rotate, commit, tag) moves to the command body.
  - Audit the rest of the SKILL.md for further sub-document candidates.

## Additional Notes
- Wave 1 (this commit range) handled: brain-review, brain-claude-md, doc-sync setup, permissions-auditor install, permissions-auditor analyze. All five became commands; `permissions-auditor` skill removed entirely.
- Naming convention going forward: commands grouped by source skill via subdirectory (`commands/<skill>/<action>.md`), surfaced by Claude Code as `/skill-cefailures:<skill>:<action>`.
