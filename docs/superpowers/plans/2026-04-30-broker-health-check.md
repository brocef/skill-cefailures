# Broker Health Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a doc-driven broker health check that Claude runs when the user asks "is broker working?" — diagnoses five common setup failures, then offers per-issue fixes.

**Architecture:** A new sub-doc at `skills/broker/docs/health-check.md` referenced from `skills/broker/SKILL.md`. The doc is the entire feature: it tells Claude how to run the diagnostic procedure, what commands to use, how to format the report, and how to walk the user through remediation. There is no Python code, no test suite, and no CLI subcommand — Claude executes the procedure by reading and following the doc.

**Tech Stack:** Markdown only. Doc invokes shell commands (bash-portable + `python3` one-liner) and existing skills (`update-config`).

**Spec:** [`docs/superpowers/specs/2026-04-30-broker-health-check-design.md`](../specs/2026-04-30-broker-health-check-design.md)

---

## File Map

- **Create** `skills/broker/docs/health-check.md` — the procedural doc Claude reads on invocation. Contains the full Phase 1 (diagnose) and Phase 2 (remediate) procedures with concrete commands, the summary table format, and the dependency cascade rules.
- **Modify** `skills/broker/SKILL.md` — add one row to the Docs table at the bottom (so Claude knows when to read `docs/health-check.md`), and add one bullet to the Prerequisites section (a discoverability hint to the user).
- **Modify** `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` — note the new feature for the next release cut.

No new Python files. No new tests in `tests/`. Verification is manual; see Task 3.

---

## Task 1: Create `skills/broker/docs/health-check.md`

The single source of truth for the feature. Claude reads this when the user invokes the health check via natural language. Content must match the spec's procedural details exactly so future maintainers can diff the doc against the spec.

**Files:**
- Create: `skills/broker/docs/health-check.md`

- [ ] **Step 1: Create the file with the full content below**

Write the file with exactly this content:

````markdown
# Broker Health Check

The user can ask Claude to diagnose their broker setup by saying things like:

- "check broker setup"
- "is broker working" / "is broker healthy"
- "diagnose broker"
- "broker doctor"
- "what's wrong with broker"

When the user asks for this, run the **two-phase procedure** below: diagnose first, then remediate failures one at a time. Do not interleave the phases. Do not offer fixes during Phase 1.

## Phase 1 — Diagnose

Run all five checks below in any order; their inputs are independent except as noted under Check 5. After all five have results, print a single summary table. Do not print any per-check output as you go — collect quietly, report once.

### Check 1: `~/.local/bin` on `$PATH`

```bash
case ":$PATH:" in *":$HOME/.local/bin:"*) echo ok;; *) echo "not on PATH";; esac
```

Pass if output is `ok`. Detail on fail: `not on PATH`.

### Check 2: broker symlink valid

```bash
test -L "$HOME/.local/bin/broker" && python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME/.local/bin/broker"
```

The `python3` one-liner is used instead of `readlink -f` because BSD `readlink` (default on macOS without GNU coreutils) does not support `-f`.

Pass criteria: `test -L` succeeds AND the resolved path is a readable file ending in `broker_cli.py`.

- If `test -L` fails: detail is `missing`.
- If `test -L` succeeds but the resolved path does not exist: detail is `dangling: <resolved-path>`.
- If the resolved path exists but does not end in `broker_cli.py`: detail is `wrong target: <resolved-path>`.

Capture the resolved path. Check 5 needs it.

### Check 3: broker server reachable

```bash
test -S "$HOME/.mcp-broker/broker.sock"
```

Pass on exit 0. This is a file-existence check only; do not perform a round-trip. Detail on fail: `no socket at ~/.mcp-broker/broker.sock`.

### Check 4: `Bash(broker:*)` permission active

Read each of these files in order, stopping at the first match:

1. `<cwd>/.claude/settings.local.json`
2. `<cwd>/.claude/settings.json`
3. `~/.claude/settings.json`

In each file, look at the `permissions.allow` array (a list of strings). Pass if any entry starts with the literal prefix `Bash(broker:` — this matches `Bash(broker:*)`, `Bash(broker:read)`, `Bash(broker:send,broker:read)`, etc.

- Detail on pass: `found in <filename>` (the first file that matched).
- Detail on fail: `not found in project or user settings`.

If a settings file exists but is not valid JSON, treat it as absent for matching but append `(<filename> malformed — skipped)` to the detail string for visibility.

### Check 5: broker version matches plugin cache

**Dependency:** if Check 2 failed (any reason), this check is skipped with status `—` and detail `depends on check 2 (symlink)`. Do not run the steps below in that case.

Otherwise:

1. Use the resolved path captured in Check 2. Call it `$RESOLVED`.
2. Test `$RESOLVED` against the regex `^<HOME>/\.claude/plugins/cache/skill-cefailures/skill-cefailures/[^/]+/scripts/broker_cli\.py$` (with `$HOME` literally expanded). If it does not match, this check is skipped with status `—` and detail `dev install at <RESOLVED>`. (This is a passing skip, not a failure.)
3. If it matches, capture the version segment as `running`.
4. List sibling version directories at `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/`. Sort lexicographically (e.g. `ls -1 ... | sort`). Take the last entry as `latest`.
5. Compare. If `running == latest`: pass. Detail: `<running>`.
6. If `running != latest`: fail. Detail: `running <running> ≠ latest cached <latest> (stale symlink)`.

> **Maintainer note:** the lexicographic sort works while the project's release stream stays single-digit (`1.x.y` with `x` and `y` < 10). When the project reaches minor 10+ or patch 10+, switch to a tuple-of-int sort key: `sorted(entries, key=lambda v: tuple(int(x) for x in v.split(".")))`.

### Summary table format

Once all five checks have results, print exactly this table, with one row per check, no leading or trailing prose, and no per-check commentary above or below:

```
| Check                          | Status | Detail                              |
|--------------------------------|:------:|-------------------------------------|
| ~/.local/bin on $PATH          |   ?    | …                                   |
| broker symlink valid           |   ?    | …                                   |
| broker server reachable        |   ?    | …                                   |
| Bash(broker:*) permission      |   ?    | …                                   |
| broker version matches plugin  |   ?    | …                                   |
```

Status values:

- `✓` — pass
- `✗` — fail
- `—` — skipped (only Check 5 can be skipped, per its dependency rules)

After the table, transition into Phase 2 with one question: name the failing checks in the order Phase 2 will offer to fix them (see below). Example: "Fix in order: broker symlink, then permission, then version drift?"

If there are no `✗` rows, skip Phase 2 entirely and tell the user "Setup looks healthy."

## Phase 2 — Remediate

For each `✗` row (not `—`), ask the user "Fix [check name]? (y/n)" one at a time in this fixed order:

1. PATH
2. broker symlink
3. `Bash(broker:*)` permission
4. broker server
5. version drift

The order reflects dependency, not severity: PATH must exist before the symlink is reachable; the symlink must exist before any `broker` invocation works; the permission must be granted before subsequent agent calls to `broker`; the server is user-action and so follows the agent-actionable items; version drift is a downstream effect of a stale symlink.

Per-check remediation procedures:

### PATH (user action required)

Tell the user to add this line to their shell rc:

```
export PATH="$HOME/.local/bin:$PATH"
```

Suggest the file based on `$SHELL`:

- `*/zsh` → `~/.zshrc`
- `*/bash` → `~/.bashrc` on Linux, `~/.bash_profile` on macOS
- anything else → "your shell's startup file"

**Do not edit shell rc files yourself.** Tell the user they will need to restart their shell or `source` the file. Mark this fix as "user action required."

### Broker symlink (auto-applied on yes)

First, find the latest cached plugin version:

```bash
ls -1 "$HOME/.claude/plugins/cache/skill-cefailures/skill-cefailures/" 2>/dev/null | sort | tail -1
```

If that returns a value (call it `<latest>`), create the symlink:

```bash
mkdir -p "$HOME/.local/bin" && ln -sf "$HOME/.claude/plugins/cache/skill-cefailures/skill-cefailures/<latest>/scripts/broker_cli.py" "$HOME/.local/bin/broker"
```

If the cache directory does not exist or is empty, the user is on a dev install. Ask them for the absolute path to their `broker_cli.py` (typically `<repo>/scripts/broker_cli.py`) and use it as the symlink target.

`ln -sf` is atomic-replace, so a stale symlink is overwritten cleanly.

### `Bash(broker:*)` permission (auto-applied on yes via update-config)

Invoke the existing `update-config` skill to add `Bash(broker:*)` to the `permissions.allow` array. Before invoking, ask the user whether to add it to:

- Project settings: `<cwd>/.claude/settings.json` (default suggestion)
- User settings: `~/.claude/settings.json`

Pass the chosen target file to update-config.

### Broker server (user action required)

Tell the user to run, in a separate terminal:

```
broker server
```

Foreground, so they can see logs and Ctrl-C it. **Do not start the server from inside this session** — backgrounding it would orphan the process and hide its logs from the user. Mark as "user action required."

### Version drift (auto-applied on yes)

Re-run the "broker symlink" remediation above. The drift is always caused by a stale symlink; recreating the symlink pointing at the latest cache directory is the fix.

## Final summary

After all yes-fixes complete, print one summary line:

```
X of Y issues fixed; Z still require user action (PATH / server, as applicable).
```

If `Z > 0`, list the user-action items as a bulleted reminder beneath. Otherwise stop after the summary line.

## Out of scope

This procedure deliberately does not:

- Edit the user's shell rc files (`.bashrc` / `.zshrc` / `config.fish` / etc.).
- Start the broker server from inside the session.
- Verify token files for reserved identities.
- Clean up stale plugin cache directories.
- Provide a continuous monitor — it runs once when invoked, reports, and exits.
````

- [ ] **Step 2: Confirm the file was created with the right content**

Run: `wc -l skills/broker/docs/health-check.md && head -1 skills/broker/docs/health-check.md`

Expected: line count is around 175–185 lines and the first line is `# Broker Health Check`.

- [ ] **Step 3: Confirm no syntax issues in the embedded shell snippets**

Run a syntax check on each shell command listed under the checks (parse-only, do not execute):

```bash
for cmd in \
  'case ":$PATH:" in *":$HOME/.local/bin:"*) echo ok;; *) echo "not on PATH";; esac' \
  'test -L "$HOME/.local/bin/broker" && python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$HOME/.local/bin/broker"' \
  'test -S "$HOME/.mcp-broker/broker.sock"' \
  'ls -1 "$HOME/.claude/plugins/cache/skill-cefailures/skill-cefailures/" 2>/dev/null | sort | tail -1' \
  'mkdir -p "$HOME/.local/bin" && ln -sf "/some/target" "$HOME/.local/bin/broker"' \
; do
  bash -n -c "$cmd" && echo "ok: $cmd" || echo "FAIL: $cmd"
done
```

Expected: every line starts with `ok:`. The doc's commands all parse as valid bash.

- [ ] **Step 4: Commit**

```bash
git add skills/broker/docs/health-check.md
git commit -m "feat(broker): add health-check sub-doc"
```

---

## Task 2: Wire `health-check.md` into `SKILL.md`

The doc only gets read by Claude if the SKILL.md routing layer points at it. Add a row to the existing Docs table and a discoverability hint in the Prerequisites section.

**Files:**
- Modify: `skills/broker/SKILL.md`

- [ ] **Step 1: Add the Docs table row**

The existing Docs table at the bottom of `skills/broker/SKILL.md` looks like:

```markdown
## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference, storage layout, display format |
| `docs/patterns.md` | Canonical patterns: wait-for-reply, broadcast, reply-all, catch-up, monitor streaming |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) |
| `docs/troubleshooting.md` | Anti-patterns and fixes — read if you catch yourself writing a loop |
| `docs/setup.md` | Install, server, reserved identities, storage layout |
```

Append one row to the bottom of that table:

```markdown
| `docs/health-check.md` | Diagnose setup; offer to fix issues — read when the user says "is broker working", "broker doctor", "diagnose broker", or similar |
```

The final table should have six rows.

- [ ] **Step 2: Add the Prerequisites hint**

The existing Prerequisites section in `skills/broker/SKILL.md` looks like:

```markdown
## Prerequisites

- The broker server must be running (`broker server` in a terminal).
- `Bash(broker:*)` must be in your `allowedTools`.
```

Append one bullet:

```markdown
- Run a `broker doctor`-style diagnostic by asking Claude to "check broker setup" — see `docs/health-check.md`. (`broker doctor` is not an actual subcommand; the phrasing is a hint to Claude about the natural-language invocation.)
```

The final list should have three bullets.

- [ ] **Step 3: Verify the file**

Run: `grep -c "health-check" skills/broker/SKILL.md`

Expected: `2` (one occurrence in Prerequisites, one in the Docs table).

- [ ] **Step 4: Commit**

```bash
git add skills/broker/SKILL.md
git commit -m "docs(broker): wire health-check sub-doc into SKILL.md routing"
```

---

## Task 3: Manual hand-test

There are no automated tests for this feature — the unit under test is "Claude reads a markdown doc and follows it." Verify each scenario by hand. Run them in any order; each is independent.

**Files:** none (verification only).

For each scenario below, start a fresh Claude session in this repo, ensure the prerequisite state is in place, then say "check broker setup" (or any of the trigger phrases listed in the doc).

- [ ] **Scenario A: All-healthy**

Prerequisites:
- `~/.local/bin` is on `$PATH`.
- `~/.local/bin/broker` is a working symlink.
- `broker server` is running (`~/.mcp-broker/broker.sock` exists).
- `Bash(broker:*)` is in `permissions.allow` somewhere.
- The symlink target's version matches the latest cached plugin (or the symlink points at a dev clone — also acceptable).

Expected: Claude prints the table with all five rows ✓ (or row 5 as `—` if dev install), then "Setup looks healthy" and stops.

- [ ] **Scenario B: Symlink missing**

Prerequisites: rename `~/.local/bin/broker` to `~/.local/bin/broker.bak` so it does not exist.

Expected:
- Row 2: ✗ with detail `missing`.
- Row 5: `—` with detail `depends on check 2 (symlink)`.
- Other rows reflect their actual state.
- Phase 2 offers to fix the symlink first. On `y`, Claude runs the `ln -sf` command and the symlink is recreated.
- Restore the renamed file after the test: `mv ~/.local/bin/broker.bak ~/.local/bin/broker` (or accept that the test left you with a fresh symlink — equivalent outcome).

- [ ] **Scenario C: Server not running**

Prerequisites: stop `broker server` and confirm `~/.mcp-broker/broker.sock` does not exist.

Expected:
- Row 3: ✗ with detail `no socket at ~/.mcp-broker/broker.sock`.
- Phase 2 offers the user-action remediation: prints `broker server` and tells the user to run it foreground in another terminal. Claude does NOT start the server itself.

- [ ] **Scenario D: Permission missing**

Prerequisites: temporarily remove any `Bash(broker:*)`-prefix entry from your settings file. (Backup the file first.)

Expected:
- Row 4: ✗ with detail `not found in project or user settings`.
- Phase 2 offers to add `Bash(broker:*)` to `permissions.allow`. Claude asks whether to use project or user settings, then invokes update-config.
- Restore the original settings file after the test.

- [ ] **Scenario E: Version drift**

Prerequisites: this is the trickiest scenario. Easiest setup:

1. Confirm at least two cached plugin versions exist under `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/`. If not, you may need to install an older version then upgrade.
2. Manually point the broker symlink at the older one: `ln -sf ~/.claude/plugins/cache/skill-cefailures/skill-cefailures/1.3.0/scripts/broker_cli.py ~/.local/bin/broker` (assuming `1.3.0` and `1.3.1` are both cached).

Expected:
- Row 2: ✓ (symlink resolves cleanly).
- Row 5: ✗ with detail `running 1.3.0 ≠ latest cached 1.3.1 (stale symlink)`.
- Phase 2 offers to fix drift; on `y`, Claude re-runs the `ln -sf` against `1.3.1`.

- [ ] **Scenario F: Trigger-phrase recognition**

Prerequisites: any state.

Test these phrasings produce the procedure (each in a fresh session):
- "check broker setup"
- "is broker working"
- "broker doctor"
- "diagnose broker"

Expected: each phrasing causes Claude to read `docs/health-check.md` and run Phase 1.

- [ ] **Scenario G: No automatic shell-rc edit**

Prerequisites: temporarily remove `~/.local/bin` from `$PATH` for the session (e.g. `PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '\.local/bin$' | paste -sd: -)`), then start Claude.

Expected:
- Row 1: ✗ with detail `not on PATH`.
- Phase 2's PATH remediation **prints** the export line and tells the user which rc file to edit. It does NOT modify any rc file.

- [ ] **Scenario H: Trigger-phrase NEGATIVE test**

Prerequisites: any state.

In a fresh session, send unrelated broker requests like:
- "send a DM to proposit-server"
- "show my broker history"

Expected: Claude does NOT run the health check. (False-trigger regression catches if the doc accidentally hijacks normal broker invocations.)

If any scenario fails, return to Task 1 or Task 2 and fix the doc.

---

## Task 4: Release notes and changelog

Add the new feature to the project's standing `upcoming.md` files for the next release cut.

**Files:**
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`

- [ ] **Step 1: Update the changelog**

Replace the contents of `docs/changelogs/upcoming.md` with:

```markdown
# Upcoming

## Added
- Broker health check — ask Claude to "check broker setup" or "diagnose broker" (and similar) to run a 5-point diagnostic of your local broker install (PATH, symlink, server, permission, version drift) and walk through fixes for any failures. Doc: `skills/broker/docs/health-check.md`.
```

If `upcoming.md` already has content from prior unreleased work, append the `## Added` section instead of replacing.

- [ ] **Step 2: Update the release notes**

Replace (or append to) `docs/release-notes/upcoming.md`:

```markdown
# Upcoming

## Broker

A new diagnostic, invoked by saying "check broker setup" or similar to Claude. It runs a quick 5-point health check on your local install — `~/.local/bin` on `$PATH`, broker symlink valid, server reachable, `Bash(broker:*)` permission active, version match between the installed broker and the latest cached plugin — then walks through fixes for any failures. Two remediations are user-action-required (PATH and starting the server); the rest Claude can apply with your confirmation.
```

- [ ] **Step 3: Commit**

```bash
git add docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "docs(broker): note health-check sub-doc in upcoming notes"
```

---

## Final verification

- [ ] Run `git log --oneline` and confirm three commits since the spec commit (`5d7e62d`): the doc creation, the SKILL.md wiring, and the upcoming-notes update.
- [ ] Run `grep -c "health-check" skills/broker/SKILL.md` → expect `2`.
- [ ] Run `ls skills/broker/docs/health-check.md` → expect the file to exist.
- [ ] Walk through the manual test scenarios in Task 3 from a fresh Claude session.
