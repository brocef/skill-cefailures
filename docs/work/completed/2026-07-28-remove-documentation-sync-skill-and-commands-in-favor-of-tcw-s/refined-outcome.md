# Refined outcome: Remove documentation-sync skill and commands in favor of TCW's

**Accepted** by the user, 2026-07-28.

## The decision

The user directed closeout explicitly: *"Drive this change to completion, let's
drop all doc sync references and then cut a minor version"*, and authorized
publication conditionally — *"You can push if tests pass and review looks good"*.
Both conditions were met before pushing (see Evidence), so the condition was
satisfied rather than waived.

The one judgment call raised during implementation — the Codex/Claude Code TCW
version split — was put to the user, who chose to update Codex and wait rather
than ship a gap. That is why the removal is safe on both surfaces.

## Evidence

- **All 10 acceptance criteria pass**, verified with the plan's own commands.
  Full table in `outcome.md`. The headline check: live references to
  `skill-cefailures:documentation-sync` went from a measured baseline of **15**
  to **0**.
- **Suite green:** `python -m pytest tests/ -q` → 53 passed.
- **Both agent surfaces confirmed on TCW 0.15.3**, each carrying the replacement
  skill, its `references/cut-version.md`, and both commands. Every `/tcw:` pointer
  written into this repo was checked against the shipped directory listing rather
  than composed from the spec.
- **Independent review** (`bllm-review-many`, two local models) over
  `865dca7..HEAD` with implementation context: gemma4 reported **no blocking
  issues**. qwen25's two "blocking" items were misreads — it quoted the applied
  fix as if it were the surviving defect, and asked for a `docs/FOLLOWUPS.md` step
  inside `## Versioning`, which belongs to the Documentation Sync section, not a
  version cut. One reviewer question was worth acting on and was verified rather
  than dismissed: `.claude-plugin/marketplace.json` does exist and its `version`
  really is nested inside `plugins[0]`, so the new `## Versioning` section's
  instruction is accurate.

## Closeout choices

| Choice | Decision |
|---|---|
| Route | Direct to `main`, then push. No PR — solo repo, and the branch is `main`. |
| Documentation | Already current. Implementation's doc gate handled `README.md`, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`. |
| Version | **Minor** — `1.16.1` → `1.17.0`, per the user's instruction and this repo's own rule that removing a skill warrants `minor`, not `patch`. |
| Fold vs. new cut | New cut. `v1.16.1` is present on `origin`, so folding into it would rewrite a published tag. Checked, not assumed. |
| Post-mortem | Not warranted. Nothing was discovered late; the one risk that materialized was caught by the gate the plan wrote for it. |

## Deferred follow-ups

None. No `docs/FOLLOWUPS.md` entry was added: this change leaves no code TODO.

The loss of `skills/documentation-sync/docs/follow-ups.md` is deliberate and
closed, not deferred — the user chose it with the alternative (upstreaming to
TCW) on the table. `docs/FOLLOWUPS.md` remains tracked in this repo's
Documentation Sync section; only the guidance on how to write its entries is
gone. If that turns out to bite, upstreaming the doc to TCW is the fix, and it is
a new request rather than unfinished business from this item.

## Notes

Two process observations worth carrying forward, both recorded in `outcome.md`:

- The changelog commit range derived at plan time is always one commit short by
  construction — the doc-sync commit cannot appear in a range computed before it
  exists. Amending after the commit is the fix.
- The plan's AC 2 grep was vacuous as first written (path anchors matched
  nothing) and was only caught by running it against the pre-work tree. Running
  an acceptance check *before* the work, to confirm it can fail, is what made the
  15→0 baseline meaningful.
