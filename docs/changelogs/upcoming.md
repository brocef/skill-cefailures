# Upcoming

## Removed (`d8bb1f2`..`5141432`)

The `documentation-sync` surface is retired in favor of the TCW plugin's copy, which had forked from it and moved ahead. Deleted:

- `skills/documentation-sync/SKILL.md`
- `skills/documentation-sync/docs/release-notes-and-changelogs.md`
- `skills/documentation-sync/docs/follow-ups.md`
- `commands/documentation-sync/setup.md`
- `commands/documentation-sync/cut-version.md`

Both directories were registered by glob (`"skills": "./skills/"`, `"commands": "./commands/"`), so deletion de-registers them; no manifest list needed an entry removed.

Before deleting, TCW 0.15.3's `skills/documentation-sync/` was diffed against all three of ours and confirmed a superset — its `references/cut-version.md` additionally carries a fold-into-an-unpushed-version workflow we never had. The sole exception is `docs/follow-ups.md`, which has no TCW counterpart; its loss is a deliberate, accepted trade-off, not an oversight.

## Changed (`d8bb1f2`..`5141432`)

- `AGENTS.md`: both `skill-cefailures:documentation-sync` invocations retargeted to `tcw:documentation-sync`, with a note that the skill ships in the TCW plugin. New `## Versioning` section carrying what was previously inline in the Generic-instructions bullet — the three version-bearing files plus the rotate/commit/tag steps. This is load-bearing: TCW's `references/cut-version.md` Step 0 looks for exactly a `## Versioning` section and falls back to a generic manual ritual without one. Installed-skills and slash-command lists drop `documentation-sync`.
- `commands/brain-style/agents-md.md`: Documentation Sync section pointer → `tcw:documentation-sync` / `/tcw:tcw-docs-sync-setup`.
- `skills/report/SKILL.md`: example skill list drops `documentation-sync`, uses `report` instead.
- `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`: `documentation-sync` keyword removed from both; Codex `shortDescription`/`longDescription` reworded to drop it. `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` never referenced it.
- `README.md`: repo-structure tree, Skills table, and Slash Commands table all drop their documentation-sync entries.

## Notes

- Tracked as tcw work item `2026-07-28-remove-documentation-sync-skill-and-commands-in-favor-of-tcw-s`, the first item in this repo's newly initialized `docs/work/` node (`tcw init work`).
- The removal was gated on TCW shipping the replacement on **both** agent surfaces. Claude Code and Codex cache plugins separately and had drifted (0.15.3 vs 0.14.1, the latter with no `documentation-sync` skill at all); the gate caught it and the work held until both were on 0.15.3.
- Historical references under `docs/changelogs/`, `docs/release-notes/`, `docs/plans/`, `docs/superpowers/`, and the completed entries in `docs/FOLLOWUPS.md` are left as written — they record what was true at the time.
