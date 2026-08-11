# Outcome: Make the plugin marketplace syncable from the claude.ai web app

All four plan tasks shipped. Eight of nine acceptance criteria are closed
locally; the ninth is not checkable from this session and is what `verify` must
hold on.

## What shipped

### Task 1 — LICENSE and license declarations (`d3c04d9`)

`LICENSE` added at the repo root: the Apache-2.0 text with the appendix
placeholder filled in as `Copyright 2026 Brian Cefali`.
`"license": "Apache-2.0"` added to `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json`. The file landed before the declarations, as
planned.

### Task 2 — Manifest metadata (`4628186`)

- `.claude-plugin/marketplace.json` — top-level `description`, `owner.email`,
  and an `author` block on the plugin entry.
- `.claude-plugin/plugin.json` — `homepage` and `repository`, matching what
  `.codex-plugin/plugin.json` already carried.
- `.agents/plugins/marketplace.json` — `description` at both levels.

`claude plugin validate .` emitted exactly one warning before this commit
(missing marketplace description) and zero after.

### Task 3 — Regression guard and symlink removal (`110418d`)

`tests/test_no_self_ancestor_symlinks.py` walks `git ls-files -s` for mode
`120000` entries and fails if any target, normalized lexically against the
link's own directory, resolves to the link or one of its ancestors.

The guard was run **before** the removal and failed, naming
`plugins/skill-cefailures` and correctly leaving `CLAUDE.md → AGENTS.md` alone.
The symlink was then removed (`plugins/` went with it, having nothing else
tracked) and `.agents/plugins/marketplace.json` repointed to `"path": "."`. Test
and removal are one commit, per the plan — committing the guard alone would have
left the suite red at a boundary.

### Task 4 — Documentation sync (`9f62b58`)

All four `CLAUDE.md` entries fired, as predicted:

- `README.md` — deleted the two-line `plugins/ skill-cefailures -> ..` block from
  Repo Structure, which task 3 made false; added a License section. The web-app
  install line was **deliberately not added** (see Deferred below).
- `docs/release-notes/upcoming.md` — the license, and the packaging fix worded as
  what changed in the repo rather than as a working web install.
- `docs/changelogs/upcoming.md` — per-file entries with commit hashes, plus the
  verification record.
- `docs/FOLLOWUPS.md` — prepended an entry for the unconfirmed sync, the
  deferred README line, and the deliberately-unanswered causation question.

## Test result

`python -m pytest tests/ -v` — **54 passed**, including the new guard.

## Where the plan was wrong

**One correction.** The plan listed Codex tree identity as an assumption to
record in `outcome.md` if `codex` was unavailable. It was available, so the check
ran and the assumption is now a measurement — the spec's third risk is retired
rather than carried.

Method: fresh clones at `4628186` (old layout, symlink present) and `110418d`
(new layout), each installed via `codex plugin add` into an isolated
`CODEX_HOME` under the scratchpad so the real `~/.codex` was never written to
(confirmed: its pre-existing `[marketplaces.skill-cefailures]` entry is untouched,
`last_updated` still `2026-07-28`). The two vendored trees differ **only** by this
change's own three edits — the `path` line, the absent `plugins/` symlink, and
the new test file. Same skills, same content, identical otherwise.

A first attempt at this comparison was invalid and discarded: it diffed the live
working repo against a clean clone, so `.git` internals, `.claude/settings.local.json`,
and `__pycache__` swamped the signal. Both sides had to be clean clones for the
diff to mean anything.

Nothing else in the spec or plan was contradicted.

## Acceptance criteria

| # | Criterion | Status |
| --- | --- | --- |
| 1 | Only `CLAUDE.md` remains a tracked symlink | ✅ verified |
| 2 | `"path": "."`, no `plugins/` reference | ✅ verified |
| 3 | `claude plugin validate .` — zero warnings | ✅ 1 → 0 |
| 4 | marketplace.json has description, owner.email, author | ✅ verified |
| 5 | Both plugin manifests agree on name/version/homepage/repository/license | ✅ verified |
| 6 | `LICENSE` exists, declared in both manifests | ✅ verified |
| 7 | Guard fails on a self-ancestor symlink | ✅ observed failing, then passing |
| 8 | `pytest tests/ -v` passes | ✅ 54 passed |
| 9 | Marketplace syncs from claude.ai | ⏸ **not checkable here** |

## Deferred

- **Criterion 9 gates nothing local and everything real.** The sync is
  server-side; it needs these commits on `main` and pushed, then the maintainer
  adding the marketplace from <https://claude.ai/code>. Until then the fix is
  plausible-and-verified-by-analogy (TCW), not confirmed on this repo.
- **The README's web-app install line** waits on that confirmation.
- **The causation question stays open** by the maintainer's explicit choice
  (spec Non-goals). Both fixes shipped together, matching the combination
  verified on TCW.

## Notes

- The `plugins/` directory is gone entirely, not just its contents — it had no
  other tracked file.
- The guard covers the symlink defect class only. Nothing mechanically protects
  the manifest metadata; this repo has no CI, so `claude plugin validate .`
  remains a manual step. Recorded in `docs/FOLLOWUPS.md`.
