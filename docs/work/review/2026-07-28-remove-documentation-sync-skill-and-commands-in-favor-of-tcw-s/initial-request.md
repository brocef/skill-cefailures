# Remove documentation-sync skill and commands in favor of TCW's

## Product changes

The `documentation-sync` skill and its two slash commands were forked into the
TCW plugin, which now carries them as `tcw:documentation-sync` (with
`references/setup.md` and `references/release-notes-and-changelogs.md`) plus the
two commands. Keeping a second copy in `skill-cefailures` means two skills with
near-identical descriptions compete for the same triggers, and the copies have
already drifted — TCW's version has content this one doesn't.

Retire this plugin's copy so TCW's is the only one. After the change,
`skill-cefailures` no longer ships a documentation-sync surface, and anything in
this repo that pointed at `skill-cefailures:documentation-sync` points at TCW's
instead.

## Technical changes

Remove `skills/documentation-sync/` and `commands/documentation-sync/`, and
update every live reference to them: plugin metadata for both agent surfaces
(`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and the marketplace
entry if affected), the README catalog, this repo's own `AGENTS.md` Documentation
Sync directive, and the incidental mentions in `commands/brain-style/agents-md.md`
and `skills/report/SKILL.md`.

Historical records — `docs/changelogs/`, `docs/release-notes/`, `docs/plans/`,
`docs/superpowers/`, and completed entries in `docs/FOLLOWUPS.md` — describe what
happened at the time and stay as written.

## Meta changes

This repo eats its own dog food: `AGENTS.md` invokes the documentation-sync skill
by name and its version-bump note lives in that section. Removing the local skill
makes this repo depend on the TCW plugin being installed for its own documented
workflow to function. That dependency is accepted, not a problem to solve here.

## Constraints

- Both agent surfaces stay in sync (Claude Code and Codex) — this is a plugin
  metadata change, so both must be updated.
- Do not touch historical documents. Changelogs, release notes, and archived
  plans are a record, not a live reference.

## Out of scope

- Any change to the TCW plugin itself. TCW already has everything it needs.
- Migrating other projects' `CLAUDE.md` files that reference
  `skill-cefailures:documentation-sync`. Only this repo is in scope.

## Notes

Two gaps were checked against TCW before deciding scope:

- **`cut-version` command.** The TCW clone inspected during this stage
  (marketplace checkout, v0.15.1 era) had no `cut-version` counterpart, and its
  SKILL.md deliberately defers version cutting to the host project. The user
  confirmed both commands have since been added to TCW in a newer version, so
  there is nothing to preserve and nothing to upstream. **Assumption to re-check
  at spec time:** verify against the installed TCW version that both commands are
  actually present before deleting this repo's copies.
- **`skills/documentation-sync/docs/follow-ups.md`.** No TCW counterpart exists.
  The user decided to delete it and accept the loss of that guidance.
  `docs/FOLLOWUPS.md` stays tracked in this repo's Documentation Sync section;
  it just no longer has a skill sub-doc explaining how to write entries.
