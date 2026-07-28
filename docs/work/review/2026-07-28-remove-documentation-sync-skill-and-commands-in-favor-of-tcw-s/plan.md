# Plan: Remove documentation-sync skill and commands in favor of TCW's

## Blocker

`tcw work edit … --blocked-by "TCW plugin release shipping tcw-cut-version +
tcw-docs-sync-setup commands and references/cut-version.md"` is set. `tcw work
start` refuses until it clears. **Task 0 is the gate that clears it.**

## Ordering rationale

The tree is markdown and metadata; `python -m pytest tests/` exercises
`create_skill.py` and `analyze_permissions.py` and is indifferent to which skills
ship. So "green at every commit boundary" is cheap here, and the real sequencing
risk is different: **the retarget must land before the delete.** If deletion goes
first, there is a commit where `AGENTS.md` invokes a skill this repo no longer
has and TCW's name is not yet written down — a state where the repo's own
documented workflow is broken. Retargeting first means every intermediate commit
points at something that exists.

Task 5 (the doc-sync pass) goes last because its changelog entry needs a commit
range that does not exist until tasks 1–4 are committed.

## Tasks

### Task 0 — Confirm the TCW replacement is installed (gate)

**Changes:** nothing. This is a check.

**Do:** resolve the installed TCW plugin directory — do not hardcode a version,
and do not use `~/Projects/TCW` (working tree) or
`~/.claude/plugins/marketplaces/tcw` (marketplace checkout); neither is what an
agent loads.

**Both agent surfaces cache separately and are currently on different versions**
(Claude Code 0.15.1, Codex 0.14.1 as of writing), so check both:

```sh
for root in ~/.claude ~/.codex; do
  d=$(ls -d "$root"/plugins/cache/tcw/tcw/*/ 2>/dev/null | sort -V | tail -1)
  echo "== $root -> ${d:-MISSING}"
  [ -n "$d" ] && ls "$d/commands/" && ls "$d/skills/documentation-sync/references/"
done
```

Each resolved directory must contain all four:

- `skills/documentation-sync/SKILL.md`
- `skills/documentation-sync/references/cut-version.md`
- `commands/tcw-cut-version.md`
- `commands/tcw-docs-sync-setup.md`

Record the **actual** command basenames from that `ls`. Every later task writes
those names, not the ones predicted in the spec. If the two surfaces disagree on
what is installed, that is a finding — report it rather than picking one.

Also re-diff this repo's `skills/documentation-sync/SKILL.md` and
`docs/release-notes-and-changelogs.md` against TCW's, confirming TCW's is a
superset (spec Notes flags this as unverified).

**Verify:** all four paths exist; the diff shows nothing in this repo's copies
that TCW lacks.

**If it fails:** stop. Do not proceed to Task 1 — the blocker has not cleared.
Report which of the four are missing.

**Then:** clear the blocker with `tcw work edit <slug>` and start the item.

---

### Task 1 — Retarget `AGENTS.md`

**Changes:** `AGENTS.md` only (`CLAUDE.md` is a symlink to it — do not edit or
recreate it).

Four edits:

1. **Line 6 splits.** The offer-the-four-outcomes clause stays in Generic
   instructions, with `` `skill-cefailures:documentation-sync` `` →
   `` `tcw:documentation-sync` ``. Its project-specific tail — the three
   version-bearing files and the `minor`-for-new-skills rule — is cut from this
   bullet and moves to the new section below.
2. **New `## Versioning` section.** Carries what was cut, plus the rotation
   steps: bump `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
   `.codex-plugin/plugin.json` together; rotate `docs/release-notes/upcoming.md`
   and `docs/changelogs/upcoming.md` to `v{version}.md`; commit; tag. Prose, not
   a script — this repo has none and is not gaining one. This is where TCW's
   cut-version looks for a project process.
3. **Line 11.** `skill-cefailures:documentation-sync` → `tcw:documentation-sync`,
   plus one sentence stating the TCW plugin must be installed for the directive
   to resolve.
4. **Line 22.** Drop `documentation-sync` from both the installed-skills list and
   the slash-commands list.

**Verify:** `grep -n "skill-cefailures:documentation-sync" AGENTS.md` → nothing;
`grep -n "tcw:documentation-sync" AGENTS.md` → the two retargeted lines;
`grep -n "^## Versioning" AGENTS.md` → present, naming all three files;
`ls -l CLAUDE.md` still shows the symlink. Covers AC 4, 5, 6, 10.

---

### Task 2 — Retarget the two incidental in-repo references

**Changes:**

- `commands/brain-style/agents-md.md:78` — `documentation-sync` skill →
  `tcw:documentation-sync`; `/skill-cefailures:documentation-sync:setup` → the
  real TCW setup command name recorded in Task 0.
- `skills/report/SKILL.md:24` — drop `documentation-sync` from the example skill
  list, leaving `brain-style`, `capabilities-sdlc`, `report`.

Leave `skills/capabilities-sdlc/SKILL.md:12` and `:51` alone — they describe the
documentation-sync *convention*, which is unchanged.

**Verify:** `grep -rn "skill-cefailures:documentation-sync" commands/ skills/` →
nothing. The TCW command named in `agents-md.md` matches a file listed in Task 0.

---

### Task 3 — Strip the plugin metadata

**Changes:** `.claude-plugin/plugin.json` (keyword at line 8),
`.codex-plugin/plugin.json` (keyword at line 13, `shortDescription` at 19,
`longDescription` at 20 — both name documentation-sync in prose and need
rewording).

Both surfaces change together, per the AGENTS.md dual-surface rule.
`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` do not
mention it — no change. Do **not** touch the `version` fields; versioning is the
user's call at completion.

**Verify:**

```
grep -c documentation-sync .claude-plugin/plugin.json .codex-plugin/plugin.json   # 0, 0
python -c "import json,sys;[json.load(open(p)) for p in sys.argv[1:]]" \
  .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json
```

Covers AC 7.

---

### Task 4 — Delete the surface

**Changes:** `git rm -r skills/documentation-sync commands/documentation-sync`,
which removes exactly these 5 files — all of them *inside* the two deleted
directories; none is a top-level `docs/` file:

- `skills/documentation-sync/SKILL.md`
- `skills/documentation-sync/docs/follow-ups.md`
- `skills/documentation-sync/docs/release-notes-and-changelogs.md`
- `commands/documentation-sync/setup.md`
- `commands/documentation-sync/cut-version.md`

The repo's own `docs/release-notes/`, `docs/changelogs/`, and `docs/FOLLOWUPS.md`
are unrelated and untouched.

Both are directory-glob registered, so no manifest edit accompanies this.

**Verify:** neither path exists; `python -m pytest tests/ -v` passes. Covers
AC 1, 8.

---

### Task 5 — Documentation Sync pass

Runs last: the changelog entry needs the commit range from tasks 1–4.

Evaluation of the four entries in `AGENTS.md`'s Documentation Sync section:

| Entry | Trigger | Fires? | Task |
|---|---|---|---|
| `README.md` | `[Public-API]` | **Yes** — the skill and command catalog *is* this plugin's public surface | 5a |
| `docs/release-notes/upcoming.md` | `[Public-API]` | **Yes** — users lose a skill and two commands | 5b |
| `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | **Yes** | 5c |
| `docs/FOLLOWUPS.md` | `[Any-Code-Change]` | **No** — the trigger fires but the entry's own description scopes it to "when feature work leaves code-related TODOs". This work leaves none; the lost `follow-ups.md` guidance is a decided trade-off, not a deferred item. Existing entries mentioning documentation-sync are history and stay. | — |

**5a — `README.md`.** Delete lines 74 and 79 from the Repo Structure tree, the
`documentation-sync` row from the Skills table (109), and both command rows from
the Slash Commands table (120–121).
*Verify:* `grep -n documentation-sync README.md` → nothing (AC 3).

**5b — `docs/release-notes/upcoming.md`.** Currently just `# Upcoming`. Add a
plain-language entry: the documentation-sync skill and its two commands have
moved to the TCW plugin; install TCW to keep using them. No jargon.

**5c — `docs/changelogs/upcoming.md`.** Currently just `# Upcoming`. Add a
developer entry with the commit hash range spanning tasks 1–4 — take it from
`git log --oneline 817bf5b..HEAD` (`817bf5b` is the spec commit, the last one
before task 1) and write it as `<first>-<last>`. List the deleted paths, the
retargeted references, the metadata edits, and the accepted loss of
`skills/documentation-sync/docs/follow-ups.md`.

*Verify 5b/5c:* both files have a non-empty entry; the changelog carries a real
range (AC 9).

---

## Verification

Run after Task 5. The suite proves almost nothing here — the checks that matter
are greps and existence checks.

```
# AC 1
test ! -e skills/documentation-sync && test ! -e commands/documentation-sync

# AC 2 — must print nothing; any line here is a live dangling pointer
grep -rn "skill-cefailures:documentation-sync" --exclude-dir=.git . \
  | grep -Ev '^(\./)?docs/(changelogs|release-notes|plans|superpowers|work)/|^(\./)?docs/FOLLOWUPS\.md:'

# AC 3, 4, 6, 10
grep -n documentation-sync README.md                    # empty
grep -n "skill-cefailures:documentation-sync" AGENTS.md # empty
grep -n "tcw:documentation-sync" AGENTS.md              # present

# AC 5 — section exists AND names all three version-bearing files
sed -n '/^## Versioning/,/^## /p' AGENTS.md \
  | grep -o -e '\.claude-plugin/plugin\.json' \
            -e '\.claude-plugin/marketplace\.json' \
            -e '\.codex-plugin/plugin\.json' | sort -u | wc -l   # expect 3

# AC 7
grep -c documentation-sync .claude-plugin/plugin.json .codex-plugin/plugin.json
python -c "import json,sys;[json.load(open(p)) for p in sys.argv[1:]]" \
  .claude-plugin/plugin.json .codex-plugin/plugin.json .claude-plugin/marketplace.json

# AC 8
python -m pytest tests/ -v
```

The AC 2 pipeline filters out the paths where historical mentions are expected —
`docs/changelogs/`, `docs/release-notes/`, `docs/plans/`, `docs/superpowers/`,
`docs/FOLLOWUPS.md`, `docs/work/` — so it is pass/fail: **empty output passes.**
Run it from the repo root; the path patterns are anchored (the optional `./`
handles grep implementations that do and don't prefix it).

**Baseline, measured before any task ran:** this pipeline currently prints 15
lines — 3 in `README.md`, 2 in `AGENTS.md`, 1 in
`commands/brain-style/agents-md.md`, 6 in `skills/documentation-sync/SKILL.md`,
2 in `commands/documentation-sync/setup.md`, 1 in
`skills/documentation-sync/docs/release-notes-and-changelogs.md`. Every one is
handled by tasks 1–5; if the count after implementation is anything but 0, diff
against this list to find what was skipped. Note the baseline contains **no**
mention in `skills/report/SKILL.md` or the two `plugin.json` files — those say
`documentation-sync` without the `skill-cefailures:` prefix, which is why AC 3
and AC 7 exist as separate checks.

**Not machine-checkable — do by hand:**

- **AC 6a, the pointer check.** For every `/tcw:<cmd>` now written into
  `AGENTS.md` and `commands/brain-style/agents-md.md`, confirm a matching
  `commands/<cmd>.md` exists in the installed TCW plugin. Compose nothing from
  memory; list the directory. A wrong name is a silent dead pointer that no grep
  catches.
- **The `## Versioning` section is actually usable.** Read it as if you were TCW's
  cut-version arriving cold: does it name every file to bump and every rotation
  step, with no dependency on the command this item just deleted?
- **`AGENTS.md` reads coherently after the line-6 split.** The offer trigger and
  the mechanics now live in two places; confirm neither half is orphaned.

## Notes

- **Self-referential edit.** Task 1 rewrites the Documentation Sync directive that
  governs this very session. Task 5 evaluates the triggers against the *finished*
  diff, using the section as it stands after Task 1 — which is the same four
  entries, so the evaluation above holds either way.
- **Versioning is deliberately not in this plan.** Removing a skill is arguably a
  `major`; `AGENTS.md` only documents `minor` for *adding* one. That is the
  user's call at completion, offered per the four-outcome rule — not decided here.
- Each task is one commit. Task 5's three sub-parts can share a commit; they are
  one doc-sync pass.
