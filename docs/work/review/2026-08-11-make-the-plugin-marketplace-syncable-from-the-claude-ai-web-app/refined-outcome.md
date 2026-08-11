# Refined outcome: Make the plugin marketplace syncable from the claude.ai web app

## Decision

**Accepted** by the maintainer on 2026-08-11, with acceptance criterion 9
knowingly open. Resolution `done`.

The maintainer chose to complete now rather than hold in `review` until the
web-app sync is confirmed. That is a deliberate call, not an oversight: every
criterion this repo can answer is answered, and the remaining one depends on
Anthropic's server-side validator reading the published repo — which cannot
happen until these commits are on `origin/main`.

## Evidence

Verified against the working tree at commit `9f62b58`, all checks re-run in one
pass at acceptance time:

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Only `CLAUDE.md` remains a tracked symlink | `git ls-files -s \| awk '$1=="120000"'` → `CLAUDE.md` alone |
| 2 | `"path": "."`, no `plugins/` | `.agents/plugins/marketplace.json:13`; `git ls-files \| grep -c '^plugins/'` → 0 |
| 3 | Zero validate warnings | `claude plugin validate .` → "Validation passed" (was 1 warning at `d3c04d9`) |
| 4 | marketplace.json metadata | `description`, `owner.email`, `plugins[0].author` all present |
| 5 | Manifests agree | `name`, `version`, `homepage`, `repository`, `license` identical across both plugin manifests |
| 6 | LICENSE declared honestly | Apache-2.0 text at repo root, `Copyright 2026 Brian Cefali`, declared in both manifests |
| 7 | Guard observed failing | Failed on the pre-fix tree naming `plugins/skill-cefailures`, ignoring `CLAUDE.md → AGENTS.md`; passes after removal |
| 8 | Suite green | `pytest tests/ -q` → 54 passed |
| 9 | Syncs from claude.ai | **Open** — see below |

**Criterion 7 is the one worth singling out.** The guard was run against the
broken tree and watched to fail before the symlink was removed. A regression test
that has only ever been seen passing is not known to guard anything.

**The spec's Codex risk was retired, not carried.** The plan allowed recording
tree identity as an assumption if `codex` was unavailable; it was available, so
the check ran. Clean clones at `4628186` (old layout) and `110418d` (new) were
each installed via `codex plugin add` into isolated `CODEX_HOME`s under the
scratchpad. The vendored trees differ only by this change's own three edits.
The real `~/.codex` was never written to — its pre-existing
`[marketplaces.skill-cefailures]` entry still reads `last_updated =
"2026-07-28T15:35:40Z"`.

## Deferred follow-ups

Logged in `docs/FOLLOWUPS.md` under "Marketplace web-app sync — unconfirmed, and
cause unknown":

1. **Confirm the sync** from <https://claude.ai/code> once published. If it still
   fails the error string will be byte-identical to before, because the server
   collapses every rejection into one message — a re-test is the only signal.
2. **Add the web-app install path to `README.md`** only after that confirmation.
   It was left out deliberately; documenting an install route nobody has
   successfully used is a promise, not a doc. The release notes are hedged for
   the same reason.
3. **The cause stays unknown** by explicit choice (spec Non-goals). Both fixes
   shipped together, matching the combination verified on `brocef/TCW`.
4. **The guard covers the symlink half only.** Nothing mechanically protects the
   manifest metadata; this repo has no CI, so `claude plugin validate .` is a
   manual step.

## Closeout choices

- **Push:** yes — the five commits go to `origin/main`. This is a precondition
  for the maintainer's own test of criterion 9, not an afterthought.
- **GitHub issue #3:** stays **open**. It is the reporter-facing record of a fix
  that has not been observed working. Closing it now would assert a result
  nobody has; it closes when the sync is confirmed.
- **Version:** patch → v1.17.1. Packaging metadata and a license, no skill added
  or removed, which is what `CLAUDE.md` reserves `minor` for.
- **Post-mortem:** not offered. Verification surfaced no unforeseen problems —
  the one plan deviation (Codex check run rather than assumed) strengthened the
  result.

## Notes

- Capabilities reconciliation is not applicable: `tcw capabilities list` reports
  no capabilities node in this project, and the change has no product delta.
- The `plugins/` directory is gone entirely, not merely emptied — it had no other
  tracked file.
