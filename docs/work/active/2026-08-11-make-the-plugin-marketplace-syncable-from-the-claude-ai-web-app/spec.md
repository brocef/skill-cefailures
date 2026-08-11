# Spec: Make the plugin marketplace syncable from the claude.ai web app

## Capability changes

None. This project has no `tcw capabilities` node (`tcw capabilities list` →
"no tcw capabilities node here"), and no taxonomy entries are affected. The
change is packaging metadata and repository layout; no skill, command, or script
behavior moves.

## Problem

`brocef/skill-cefailures` cannot be added as a marketplace from
<https://claude.ai/code> or the Claude Desktop plugin directory. The sync fails
with the generic string *"Marketplace sync failed. Check the repository URL and
try again."* The CLI path (`claude plugin marketplace add …`) is unaffected — the
web/desktop flow validates server-side and is stricter.

Two defects in this repo are candidates, both confirmed present:

1. **A self-referential tracked symlink.** `plugins/skill-cefailures` is a mode
   `120000` entry pointing at `..` (verified: `git ls-files -s | awk '$1=="120000"'`
   lists exactly two symlinks — `CLAUDE.md → AGENTS.md`, benign, and
   `plugins/skill-cefailures → ..`). Because `.claude-plugin/marketplace.json:9`
   declares `"source": "./"`, the plugin root contains itself:
   `plugins/skill-cefailures/plugins/skill-cefailures/…` with no end. Any
   component scan that follows symlinks recurses without termination.

2. **Missing manifest metadata.** `.claude-plugin/marketplace.json` has no
   top-level `description` (the sole warning from `claude plugin validate .`), no
   `owner.email` (`owner` at line 3 carries only `name`), and no `author` on the
   plugin entry. `.agents/plugins/marketplace.json` has no `description` at
   either level.

Two manifests also disagree about the same artifact: `.codex-plugin/plugin.json`
carries `homepage` and `repository`; `.claude-plugin/plugin.json` carries
neither. Neither declares a license, and the repo has no `LICENSE` file — no
file in this repo declares one anywhere (the skills' own frontmatter carries no
`license:` field either).

The same two defects were fixed together on the sibling repo `brocef/TCW`, which
failed identically and now syncs from the web app. That is the only end-to-end
verification that exists.

## Goals

- The marketplace syncs from the claude.ai web app and the Desktop plugin
  directory.
- The three manifests describe one artifact consistently.
- The defect *class* — a tracked symlink resolving to its own ancestor — cannot
  silently return.
- The repo carries a real license, declared honestly.

## Non-goals

- **Determining which of the two fixes satisfied the validator.** Both are
  applied in one pass, matching the verified TCW combination. The maintainer
  chose speed over the causation answer; it stays unanswered.
- Changing what the plugin ships — no skill, command, script, or `source`/`path`
  semantics change. `"."` and `"./plugins/skill-cefailures"` resolve to the same
  repo root, so the installed tree is byte-identical.
- Any change to the CLI install path, which already works.
- Removing `CLAUDE.md → AGENTS.md`. It is a symlink but not a self-ancestor, and
  it serves a real purpose (two agent surfaces, one file).

## Design

**1. Delete the self-symlink; address the plugin root-relatively.**

`git rm plugins/skill-cefailures`, and in `.agents/plugins/marketplace.json:11`
change `"path": "./plugins/skill-cefailures"` → `"path": "."`. The `plugins/`
directory then contains nothing tracked and disappears.

**2. Complete `.claude-plugin/marketplace.json`.** Add top-level `description`,
`owner.email`, and an `author` block on the plugin entry mirroring
`.claude-plugin/plugin.json`'s.

**3. Align the three manifests.** Add `homepage` and `repository` to
`.claude-plugin/plugin.json` to match `.codex-plugin/plugin.json`. Add
`description` at both levels of `.agents/plugins/marketplace.json`.

**4. License.** Add an Apache-2.0 `LICENSE` file at the repo root, then declare
`"license": "Apache-2.0"` in both `.claude-plugin/plugin.json` and
`.codex-plugin/plugin.json`. The file comes first; the declaration follows it,
never the reverse.

**5. Regression guard.** A test asserting the class, not the instance: walk
`git ls-files -s` for mode `120000` entries, resolve each target, and fail if
any resolves to an ancestor of its own path. Lives in `tests/` alongside the two
existing pytest modules (`test_analyze_permissions.py`, `test_create_skill.py`).
Pinning `plugins/skill-cefailures` by name would only stop that one path from
returning.

**Sibling-defect sweep (repo-wide).** Both defect classes were swept across the
whole repo, not just the paths the issue named:

- *Self-ancestor symlinks:* `git ls-files -s` returns exactly two `120000`
  entries repo-wide. `CLAUDE.md → AGENTS.md` is not a self-ancestor;
  `plugins/skill-cefailures → ..` is the only instance.
- *Manifest disagreement:* all three manifests were read in full. The
  divergences are the ones listed above; there are no others.

## Acceptance criteria

1. `git ls-files -s | awk '$1=="120000"'` lists `CLAUDE.md` and nothing else.
2. `.agents/plugins/marketplace.json` has `"path": "."` and no reference to
   `plugins/`.
3. `claude plugin validate .` passes with **zero warnings** (currently one:
   missing marketplace description).
4. `.claude-plugin/marketplace.json` has a top-level `description`, an
   `owner.email`, and an `author` on the plugin entry.
5. `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` agree on `name`,
   `version`, `homepage`, `repository`, and `license`.
6. A `LICENSE` file exists at the repo root containing the Apache-2.0 text, and
   `"license": "Apache-2.0"` appears in both plugin manifests.
7. A test in `tests/` fails if any tracked symlink resolves to an ancestor of its
   own path — verified by temporarily reintroducing such a symlink and watching
   it fail, not by assuming.
8. `python -m pytest tests/ -v` passes.
9. **Maintainer-verified:** adding `brocef/skill-cefailures` from
   <https://claude.ai/code> syncs and the plugin becomes installable.

## Risks

- **Criterion 9 cannot be checked from this session.** The web sync is
  server-side and reachable only by the maintainer, after the change is pushed
  to `main`. Every other criterion is locally checkable; this one gates real
  closure and must be held open until the maintainer tests it.
- **The fix may not be sufficient.** The server-side validator collapses every
  rejection into one string, so if sync still fails after this, the error will
  say nothing new. TCW's success is strong evidence but not proof that these are
  the only two things this repo trips on.
- **Codex regression.** The `path` change alters how `codex-cli` resolves the
  plugin. The issue reports both layouts resolving to the repo root and vendoring
  an identical tree on TCW against `codex-cli 0.147.0`; that is a measurement on
  a different repo, so it is an assumption here until the tree is diffed.
- **Declaring Apache-2.0 is a new choice**, not a reconciliation — nothing in
  this repo declared a license before. It is the maintainer's decision, recorded
  here, and it applies retroactively to all existing code.

## Notes

- The issue's own causation caveat is honest and worth preserving: TCW changed
  both things at once, so which one the validator objected to is unknown. This
  item deliberately does not answer it.
- Ruled out by TCW's result: the earlier hypothesis that claude.ai resolves
  repos owned by the signed-in user through an uninstalled GitHub App. If that
  were the cause, no repository change could have fixed TCW.
