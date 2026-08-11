# Follow-ups

Standing log of deferred code-related follow-up items. New entries are prepended; completed items are annotated in place (strikethrough + completion date), not deleted.

# Marketplace web-app sync — unconfirmed, and cause unknown
Commit range: d3c04d9-110418d
Branch name: main
Added on: 2026-08-11

## Follow-up Items
- **Confirm the fix.** Adding `brocef/skill-cefailures` from <https://claude.ai/code> has not been tested since the change; it needs these commits published first. This is acceptance criterion 9 of `docs/work/.../2026-08-11-make-the-plugin-marketplace-syncable-from-the-claude-ai-web-app` and the only one that did not close locally. If it still fails, the error string will be byte-identical to before — the server collapses every rejection into one message — so a re-test is the only signal.
- **Add the web-app install path to `README.md`** once the above is confirmed. It was deliberately left out of the Installation section: documenting an install route nobody has successfully used is a promise, not a doc.
- **The cause is deliberately unknown.** Both candidate fixes (self-symlink removal, manifest metadata) shipped in one pass, matching the combination verified on `brocef/TCW`. The maintainer chose that over bisecting. Answering it would mean reverting one, re-testing, and reverting the other — cheap, but only worth doing if the answer matters for a third repo.

## Additional Notes
- The regression guard covers only the symlink half. Nothing mechanically prevents the manifest metadata from being emptied again; `claude plugin validate .` warns on a missing marketplace description but is not run in CI, and the repo has no CI.

# Retire the docs/inbox pattern
Commit range: 989eed6-HEAD
Branch name: main
Added on: 2026-07-15

## Follow-up Items
- Implement the Markdown-preferring WebFetch hook specified in `docs/plans/2026-06-17-claude-code-markdown-web-fetch-hook.md`. A `PreToolUse` hook matching `WebFetch` that discovers a Markdown representation (Accept-header content negotiation → HTTP `Link` header → HTML head `<link rel="alternate">` → HTML-to-Markdown fallback) and returns `updatedInput` with the rewritten URL plus `additionalContext` naming the canonical original. The spec carries open design questions (same-origin vs. cross-origin policy, cache location, Python HTML-to-Markdown library choice) that need answers before implementation. Codex parity is deliberately deferred — Codex hooks have no documented `updatedInput` equivalent, so parity would come later via a shared MCP `smart_fetch` tool. Moved here from `docs/inbox/` when that folder was retired; it was never processed.
- `docs/plans/2026-07-13-remove-proposit-dependencies.md` is now partially moot — its tasks for `commands/process-inbox-initiative.md` and for generalizing the anti-volatility inbox request both refer to files that no longer exist. Re-scope or close the plan.

## Additional Notes
- The `docs/inbox/` convention is superseded by the TCW work axis. The `process-inbox` commands were retired outright rather than scoped, per maintainer decision: no known non-TCW consumer still uses a bare `docs/inbox/` folder.

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
