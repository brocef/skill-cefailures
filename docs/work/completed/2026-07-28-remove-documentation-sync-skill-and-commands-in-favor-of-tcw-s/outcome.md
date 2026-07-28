# Outcome: Remove documentation-sync skill and commands in favor of TCW's

All five plan tasks shipped as planned. 17 files changed, 64 insertions, 423
deletions. Suite green: 53 passed.

## What shipped, task by task

| Task | Commit | What |
|---|---|---|
| 0 — gate | (no commit) | Verified TCW 0.15.3 ships `skills/documentation-sync/{SKILL.md,references/cut-version.md}` and `commands/{tcw-cut-version,tcw-docs-sync-setup}.md` on **both** agent caches; confirmed TCW's copies are a superset of ours |
| 1 | `d8bb1f2` | `AGENTS.md` retargeted at `tcw:documentation-sync`; new `## Versioning` section; installed-skills/commands lists trimmed |
| 2 | `d0686b0` | `commands/brain-style/agents-md.md` → `/tcw:tcw-docs-sync-setup`; `skills/report/SKILL.md` example list |
| 3 | `93c975d` | `documentation-sync` keyword dropped from both `plugin.json`s; Codex descriptions reworded |
| 4 | `0fbda15` | `git rm -r skills/documentation-sync commands/documentation-sync` — exactly the 5 predicted files |
| 5 | `66cc9e5` | Documentation Sync pass: `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md` |

## Acceptance criteria

All 10 pass, verified by the plan's own commands:

| AC | Result |
|---|---|
| 1 — both directories gone | PASS |
| 2 — no live `skill-cefailures:documentation-sync` | PASS (0 lines, from a baseline of 15) |
| 3 — `README.md` clean | PASS |
| 4 — `AGENTS.md` has no old reference | PASS (0) |
| 5 — `## Versioning` names all three files | PASS (3/3) |
| 6 — installed-skills list trimmed | PASS |
| 6a — TCW pointers resolve | PASS, both caches |
| 6b — replacement installed | PASS, both caches on 0.15.3 |
| 7 — manifests clean + valid JSON | PASS (0, 0; JSON ok) |
| 8 — suite green | PASS (53 passed) |
| 9 — release notes + changelog with range | PASS (`d8bb1f2`..`5141432`) |
| 10 — TCW plugin dependency stated | PASS |

## Where the plan was right in a way worth recording

**The Task 0 gate earned its place.** It was written to catch a stale TCW
install, and it caught one the session would otherwise have missed: after
`/plugin` updated TCW, Claude Code was on **0.15.3** while Codex was still on
**0.14.1** — a version with no `documentation-sync` skill at all. Deleting then
would have left Codex with the skill available from neither plugin, silently
violating this repo's dual-surface rule. Work held until both caches were on
0.15.3.

The plan's instruction to *read* the installed command names rather than compose
them also paid: the spec predicted `/tcw:tcw-cut-version` and
`/tcw:tcw-docs-sync-setup`, and those turned out correct — but they were
confirmed against the shipped directory before being written into `AGENTS.md`,
not assumed.

## Where the plan was wrong

Nothing material. Three small deviations:

1. **`tcw work edit --clear-blocked-by` does not exist.** The flag is
   `--unblocked-by`, and it needs the blocker's full text including the
   `external: ` prefix that `tcw work show` displays. Cosmetic; no plan change
   needed.
2. **The changelog commit range needed extending after Task 5 was committed.**
   The plan derived the range from `git log 817bf5b..HEAD`, which cannot include
   the doc-sync commit itself — that commit does not exist until the entry is
   written. Resolved by amending the range to `d8bb1f2`..`5141432` after
   committing. A plan that says "take the range from `817bf5b..HEAD`" will always
   be one commit short by construction; worth knowing next time.
3. **The plan's AC 2 grep was broken when written and was fixed at plan time**,
   not implementation time — `./`-anchored path patterns matched nothing because
   this environment's grep emits bare paths. Recorded here because the bug class
   (an acceptance check that passes vacuously) is the kind that makes a green
   verification meaningless.

## Notes

- `skills/capabilities-sdlc/SKILL.md:12` still says "documentation-sync rules"
  and was deliberately left alone — it names the convention, not the deleted
  skill. It is the only remaining bare mention outside the intentional
  `tcw:documentation-sync` retargets.
- No capability ledger work: this node was initialized with the `work` component
  only.
- No new `docs/FOLLOWUPS.md` entry — the change leaves no code TODO. The loss of
  `skills/documentation-sync/docs/follow-ups.md` is a decided trade-off, recorded
  in the spec and the changelog, not a deferred item.
- Version cut deliberately excluded from these commits; it belongs after
  `tcw work complete`.
