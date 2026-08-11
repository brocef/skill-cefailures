# Plan: Make the plugin marketplace syncable from the claude.ai web app

Four tasks. The symlink removal is the risky one and sits third — after the
safe metadata work, with its regression test written in the same commit so the
suite is green at every boundary. Docs are one block at the end.

## Task 1 — Add a LICENSE and declare it

**Changes:** new `LICENSE` at the repo root (Apache-2.0 full text);
`"license": "Apache-2.0"` added to `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json`.

**Order reason:** the file must exist before anything declares it. Declaring
first would put the repo in the exact state the issue warns against.

**Verified by:** `LICENSE` exists and contains the Apache-2.0 text; both plugin
manifests parse as JSON (`python -c 'import json,sys;[json.load(open(p)) for p in sys.argv[1:]]' .claude-plugin/plugin.json .codex-plugin/plugin.json`) and both carry the `license` key. Covers acceptance criterion 6.

## Task 2 — Complete and align the manifest metadata

**Changes:**

- `.claude-plugin/marketplace.json` — add top-level `description`, add
  `owner.email`, add an `author` block on the plugin entry mirroring
  `.claude-plugin/plugin.json`'s.
- `.claude-plugin/plugin.json` — add `homepage` and `repository`, matching the
  values already in `.codex-plugin/plugin.json`.
- `.agents/plugins/marketplace.json` — add `description` at the top level and on
  the plugin entry.

**Verified by:** `claude plugin validate .` passes with **zero** warnings (it
currently emits exactly one, for the missing marketplace description — so this
is a real before/after, not a tautology). All three manifests parse. Covers
acceptance criteria 3, 4, and the `homepage`/`repository` half of 5.

## Task 3 — Regression guard, then remove the self-symlink

**Changes:**

- New `tests/test_no_self_ancestor_symlinks.py` — walks `git ls-files -s` for
  mode `120000` entries, resolves each target relative to the symlink's own
  directory, and fails if the resolved path is an ancestor of (or equal to) the
  symlink's path. Asserts the **class**, not the path.
- `git rm plugins/skill-cefailures` (the `plugins/` directory then has nothing
  tracked left in it).
- `.agents/plugins/marketplace.json:11` — `"path": "./plugins/skill-cefailures"`
  → `"path": "."`.

**Order reason:** the test and the removal ship in one commit deliberately. The
test fails on the current tree, so committing it alone would leave the suite red
at a boundary. Splitting them into two commits would trade the guarantee the
plan is built on for nothing.

**Verified by:**

1. Run the new test **before** removing the symlink and confirm it **fails**,
   naming `plugins/skill-cefailures`. A guard never observed failing is not
   known to guard anything.
2. Remove the symlink, run it again, confirm it passes.
3. `git ls-files -s | awk '$1=="120000"'` lists `CLAUDE.md` and nothing else.
4. `python -m pytest tests/ -v` fully green.

Covers acceptance criteria 1, 2, 7, 8.

## Task 4 — Documentation Sync

Evaluated against the four entries in `CLAUDE.md`. Three fire; one is a
judgment call resolved below.

### 4a — `README.md` [Public-API] — **fires**

`README.md:83-84` documents the symlink as a real part of the repo layout:

```
plugins/
  skill-cefailures -> ..      # Codex marketplace pointer to the repo-root plugin
```

Task 3 deletes it, so the README's structure block becomes factually wrong the
moment that lands. Remove those two lines. Also add a short License section
naming Apache-2.0, since the repo now carries one.

**Deliberately deferred:** do **not** add a "install from claude.ai" line to the
Installation section in this pass. That claim is acceptance criterion 9, which
this session cannot check — see Verification. It goes in only after the
maintainer confirms the sync actually works.

### 4b — `docs/release-notes/upcoming.md` [Public-API] — **fires**

User-facing and plain: the plugin now carries an Apache-2.0 license, and the
packaging was fixed so the marketplace can be added from the web app and Desktop
plugin directory. **Word the sync fix as what changed in the repo, not as a
promise that the web app now works** — until criterion 9 is checked, "should now
sync" is the honest claim and "now syncs" is not.

### 4c — `docs/changelogs/upcoming.md` [Any-Code-Change] — **fires**

Behavior-affecting: a tracked path removed, a marketplace source path changed, a
new test module. Entry with the commit hash range for tasks 1–3.

### 4d — `docs/FOLLOWUPS.md` [Any-Code-Change] — **fires**

This work deliberately leaves one question open: the spec's Non-goals record
that both fixes ship together, so which one satisfied the server-side validator
stays unknown. Prepend an entry (commit range, branch `main`, date 2026-08-11)
recording it, plus the two conditional items — adding the web-app install path
to the README once sync is confirmed, and re-opening this if it still fails.

## Verification

Beyond the suite:

- **`claude plugin validate .` warning count** — the only mechanical check that
  the metadata work did anything. Run it before task 2 (one warning) and after
  (zero).
- **The guard must be seen failing** before the symlink is removed. Task 3 step
  1 exists because a green test on a fixed tree proves nothing about whether it
  would have caught the defect.
- **Codex tree identity is an assumption, not a check.** The spec's risk list
  flags it: the claim that `"."` and `"./plugins/skill-cefailures"` vendor an
  identical tree was measured on TCW against `codex-cli 0.147.0`, not here. If
  `codex` is available locally, install from both layouts and diff the vendored
  trees; if it is not, say so in `outcome.md` and leave it an assumption rather
  than reporting it verified.
- **Acceptance criterion 9 cannot be checked from this session.** The web sync
  is server-side, needs the change pushed to `main`, and needs the maintainer to
  add the marketplace from <https://claude.ai/code>. `verify` must hold on this;
  every other criterion closes locally. This is also why 4a defers the README
  install line and 4b hedges its wording — the docs must not assert something
  nobody has observed.

## Notes

- No blockers to record: nothing else in `docs/work/` touches packaging.
- GitHub issue #3 is the origin (`initial-request.md` → `## Origin`); closing it
  is a `complete`-stage step, gated on criterion 9, not on the merge.
