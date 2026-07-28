# Spec: Remove documentation-sync skill and commands in favor of TCW's

## Capability changes

None. This node was initialized with the `work` component only — there is no
taxonomy or capabilities ledger here (`tcw capabilities list` → "no tcw
capabilities node here"). The user-visible delta is recorded in the README
catalog and release notes instead.

## Problem

`skills/documentation-sync/` and `commands/documentation-sync/` in this repo are
a fork of what the TCW plugin now ships as `tcw:documentation-sync`. Two
consequences:

1. **Trigger collision.** The two SKILL.md `description` fields are identical but
   for one word (`skills/documentation-sync/SKILL.md:3` says "after completing
   any development work"; TCW's says "after completing development work"). Both
   plugins are installed, so an agent sees two skills claiming the same job.
2. **The fork has already drifted, and TCW's copy is ahead.** Diffing the two:
   TCW's adds project-defined trigger vocabulary (documenting
   `[Skill-Driven-Component]` as an example), names the lifecycle points that
   invoke the skill, and replaces the hardcoded `:cut-version` pointer with
   "defer to the project's own version-cut process". This repo's copy has none of
   that. The only content unique to this repo is
   `skills/documentation-sync/docs/follow-ups.md`, which TCW has no counterpart
   for.

## Goals

- `skill-cefailures` ships no documentation-sync skill or commands.
- Every live in-repo reference points at TCW's surface or is removed; no dangling
  `/skill-cefailures:documentation-sync:*` pointer survives.
- This repo's own documentation-sync workflow keeps working under
  `tcw:documentation-sync`, including the version-cut path.
- Both agent surfaces (Claude Code and Codex) stay in sync.

## Non-goals

- Changing the TCW plugin. Its side of this is already in flight (see Risks).
- Preserving `docs/follow-ups.md`. The user decided to delete it and accept the
  loss of that guidance.
- Editing historical records: `docs/changelogs/v*.md`, `docs/release-notes/v*.md`,
  `docs/plans/*`, `docs/superpowers/*`, and the completed entries in
  `docs/FOLLOWUPS.md`. They describe what was true when written.
- Migrating other repos whose `CLAUDE.md` invokes
  `skill-cefailures:documentation-sync`.

## Design

### 1. Delete the surface

Remove both directories outright:

- `skills/documentation-sync/` — `SKILL.md`, `docs/follow-ups.md`,
  `docs/release-notes-and-changelogs.md`
- `commands/documentation-sync/` — `setup.md`, `cut-version.md`

Both are declared by directory glob (`.claude-plugin/plugin.json:9-10` point at
`./skills/` and `./commands/`), so deletion alone de-registers them; no manifest
list needs an entry removed.

### 2. Move this repo's version-bump specifics into a `## Versioning` section

This is the one change that is not a mechanical find-and-replace, and it is
required rather than optional.

TCW's replacement command (`commands/tcw-cut-version.md` in the TCW working tree)
says: *"Check for the project's own version-cut process first (its `CLAUDE.md`
Versioning section, usually a script) and run that instead of cutting by hand."*
TCW's `references/cut-version.md` is reached the same way. This repo has **no**
`## Versioning` section — its bump specifics are buried in a Generic-instructions
bullet (`AGENTS.md:6`), which names the three version-bearing files
(`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
`.codex-plugin/plugin.json`) and the `minor`-for-new-skills rule.

So `AGENTS.md:6` splits:

- The **offer trigger** ("after a substantial set of changes, offer the four
  outcomes") stays a generic instruction, retargeted at `tcw:documentation-sync`.
- The **project-specific bump mechanics** — the three files to bump together and
  the `minor`-not-`patch` rule for new skills — move to a new `## Versioning`
  section, where TCW's cut-version will look for them.

Without this, the removal silently degrades: TCW's cut-version finds no project
process and falls back to a manual ritual that does not know this repo bumps
three files.

**Prose, not a script.** TCW's own Versioning section names
`python scripts/cut_version.py`; this repo has no such script and gaining one is
out of scope. The `## Versioning` section carries the steps as prose — the three
files to bump, rotate `upcoming.md` → `v{version}.md` in both
`docs/release-notes/` and `docs/changelogs/`, commit, tag. TCW's cut-version
reads a Versioning section as free text, so prose is sufficient; there is no
schema to conform to.

### 2a. Record the TCW plugin dependency

`AGENTS.md` currently describes a self-contained workflow. After this change its
Documentation Sync directive names a skill that ships in a *different* plugin, so
the section states that plainly — one sentence noting the TCW plugin must be
installed for the directive to resolve. Without it, a reader hitting
`tcw:documentation-sync` with TCW absent has no way to know what is missing.

### 3. Retarget the remaining live references

| Location | Current | Becomes |
|---|---|---|
| `AGENTS.md:6` | offer options from `` `skill-cefailures:documentation-sync` `` + inline bump mechanics | offer clause names `` `tcw:documentation-sync` ``; mechanics move to `## Versioning` (see §2) |
| `AGENTS.md:11` | "invoke the `skill-cefailures:documentation-sync` skill" | "invoke the `tcw:documentation-sync` skill" |
| `AGENTS.md:22` | skills list includes `documentation-sync`; commands list includes `documentation-sync` | both entries dropped |
| `README.md:74` | `documentation-sync/  # /skill-cefailures:documentation-sync:* commands` | line removed from the tree |
| `README.md:79` | `documentation-sync/` under `skills/` | line removed from the tree |
| `README.md:109` | `documentation-sync` row in the **Skills** table | row removed |
| `README.md:120-121` | `:setup` and `:cut-version` rows in the **Slash Commands** table | rows removed |
| `commands/brain-style/agents-md.md:78` | "used by the `documentation-sync` skill. See `/skill-cefailures:documentation-sync:setup`…" | points at `tcw:documentation-sync` and `/tcw:tcw-docs-sync-setup` |
| `skills/report/SKILL.md:24` | example skill list includes `documentation-sync` | example list drops it (`brain-style`, `capabilities-sdlc`, `report` remain) |

`skills/capabilities-sdlc/SKILL.md:12` and `:51` mention "documentation-sync
rules" and "Documentation Sync entry" generically — the *convention*, not this
plugin's skill. They stay as written.

`.codex-plugin/plugin.json:19-20` (`shortDescription` / `longDescription`) name
documentation-sync in prose; both need rewording. `.claude-plugin/plugin.json:8`
and `.codex-plugin/plugin.json:13` list it as a keyword; drop it from both.
`.agents/plugins/marketplace.json` does not mention it — no change.

### 4. Documentation Sync pass

This repo's own tracked entries all fire:

- `README.md` [Public-API] — covered by §3.
- `docs/release-notes/upcoming.md` [Public-API] — a removal is user-facing.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — with the commit range.
- `docs/FOLLOWUPS.md` [Any-Code-Change] — this leaves no code TODO, so no new
  entry. Existing entries mentioning documentation-sync are history; untouched.

## Acceptance criteria

1. `skills/documentation-sync/` and `commands/documentation-sync/` do not exist.
2. `grep -rn "skill-cefailures:documentation-sync" --exclude-dir=.git .` returns
   matches only under `docs/changelogs/`, `docs/release-notes/`, `docs/plans/`,
   `docs/superpowers/`, `docs/FOLLOWUPS.md`, and `docs/work/`.
3. `grep -rn "documentation-sync" README.md` returns nothing.
4. `AGENTS.md` contains `tcw:documentation-sync` and does not contain
   `skill-cefailures:documentation-sync`.
5. `AGENTS.md` has a `## Versioning` section naming all three version-bearing
   files — `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
   `.codex-plugin/plugin.json` — and the `minor`-for-new-skills rule.
6. `AGENTS.md:22`'s installed-skills and slash-command lists no longer name
   `documentation-sync`.
6a. **Every TCW pointer written into this repo resolves to a file that exists.**
   For each `/tcw:<cmd>` referenced in `AGENTS.md` and
   `commands/brain-style/agents-md.md`, a matching `commands/<cmd>.md` exists in
   the installed TCW plugin, and `skills/documentation-sync/SKILL.md` exists
   there too. Check by resolving the installed TCW plugin directory and listing
   it — do not compose the names from this spec. Expected as of writing:
   `/tcw:tcw-cut-version` and `/tcw:tcw-docs-sync-setup`, but the TCW commits are
   not landed yet, so treat these as *predictions to confirm*, not facts.
6b. **The TCW replacement is actually installed.** An installed (not
   working-tree) TCW plugin version contains
   `skills/documentation-sync/references/cut-version.md` plus both commands from
   6a. This is the blocking gate from Risks; it is checked before any deletion.
7. Neither `.claude-plugin/plugin.json` nor `.codex-plugin/plugin.json` contains
   the string `documentation-sync`; both remain valid JSON
   (`python -c "import json,sys;[json.load(open(p)) for p in sys.argv[1:]]" …`).
8. `python -m pytest tests/ -v` passes.
9. `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` each have an
   entry for the removal, the changelog entry carrying a commit range.
10. `AGENTS.md`'s Documentation Sync section states that the TCW plugin must be
    installed for the `tcw:documentation-sync` directive to resolve.

## Risks

- **The TCW replacement is not released yet.** `/Users/brian/Projects/TCW` has
  `commands/tcw-cut-version.md`, `commands/tcw-docs-sync-setup.md`, and
  `skills/documentation-sync/references/cut-version.md` as untracked files, and
  no installed TCW version (latest cached: 0.15.1) contains them. Deleting this
  repo's copies before TCW ships leaves a window with no working cut-version
  anywhere. **This item is blocked on a TCW release containing both commands** —
  verify at implement time, not by trusting this spec.
- **Command-name drift.** TCW names them `/tcw:tcw-cut-version` and
  `/tcw:tcw-docs-sync-setup` — not the `documentation-sync:` group naming this
  repo used. Read the shipped TCW `commands/` directory and copy the real names
  rather than composing them; a wrong name in `AGENTS.md` is a silent dead
  pointer.
- **Self-referential edit.** Changing `AGENTS.md`'s Documentation Sync directive
  changes the rules governing the session making the change. Land the doc-sync
  pass (§4) as its own commit, evaluated against the finished diff.
- **`docs/follow-ups.md` guidance is lost.** Accepted by the user.
  `docs/FOLLOWUPS.md` stays tracked in the Documentation Sync section but no
  skill explains its entry format any more.

## Notes

- **Assumption, unverified at spec time:** that TCW's shipped `references/`
  content is a superset of this repo's `SKILL.md` and
  `docs/release-notes-and-changelogs.md`. Verified against the marketplace
  checkout (TCW ahead on every diff hunk except formatting), but TCW's working
  tree has since moved. Re-diff before deleting.
- The two SKILL.md copies also differ in markdown table formatting (TCW's are
  prettier-aligned). Irrelevant to this item; noted so a future reader does not
  mistake it for content drift.
