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

`os.path.realpath` does **not** error on a dangling symlink — it returns the would-be target as a string regardless of whether it exists. After capturing the resolved path, verify it actually exists with a separate test:

```bash
python3 -c 'import os,sys; sys.exit(0 if os.path.isfile(sys.argv[1]) else 1)' "$RESOLVED"
```

Then map the four outcomes:

- `test -L` fails → fail. Detail: `missing`.
- `test -L` succeeds but the existence check fails → fail. Detail: `dangling: <resolved-path>`.
- Existence check succeeds but the path does not end in `broker_cli.py` → fail. Detail: `wrong target: <resolved-path>`.
- Existence check succeeds and the path ends in `broker_cli.py` → pass.

Capture the resolved path on pass. Check 5 needs it.

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

If a settings file exists but is not valid JSON, treat it as absent for matching purposes. Then, in the final detail string Claude prints (whichever path applies — pass detail or fail detail), append `(<filename> malformed — skipped)` so the user sees that the file was inspected but skipped.

### Check 5: broker version matches plugin cache

**Dependency:** if Check 2 failed (any reason), this check is skipped with status `—` and detail `depends on check 2 (symlink)`. Do not run the steps below in that case.

Otherwise:

1. Use the resolved path captured in Check 2. Call it `$RESOLVED`.
2. Test whether `$RESOLVED` looks like an installed-plugin path. The path qualifies if:
   - it begins with the user's `$HOME` directory (expanded at runtime), AND
   - the rest of the path matches the suffix `/.claude/plugins/cache/skill-cefailures/skill-cefailures/<ver>/scripts/broker_cli.py`, where `<ver>` is one path segment with no slashes.

   If it does not match, this check is skipped with status `—` and detail `dev install at <RESOLVED>`. (This is a passing skip, not a failure.)
3. If it matches, capture the `<ver>` segment as `running`.
4. List sibling version directories at `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/`. Sort lexicographically (e.g. `ls -1 ... | sort`). Take the last entry as `latest`.
5. Compare. If `running == latest`: pass. Detail: `<running>`.
6. If `running != latest`: fail. Detail: `running <running> ≠ latest cached <latest> (stale symlink)`.

> **Maintainer note:** the lexicographic sort works while the project's release stream stays single-digit (`1.x.y` with `x` and `y` < 10). When the project reaches minor 10+ or patch 10+, switch to a tuple-of-int sort key: `sorted(entries, key=lambda v: tuple(int(x) for x in v.split(".")))`.

### Summary table format

Once all five checks have results, print exactly this table, with one row per check, no leading or trailing prose, and no per-check commentary above or below:

```
| Check                          | Status | Detail                              |
|--------------------------------|:------:|-------------------------------------|
| ~/.local/bin on $PATH          |  <s>   | <d>                                 |
| broker symlink valid           |  <s>   | <d>                                 |
| broker server reachable        |  <s>   | <d>                                 |
| Bash(broker:*) permission      |  <s>   | <d>                                 |
| broker version matches plugin  |  <s>   | <d>                                 |
```

`<s>` and `<d>` are placeholders. Replace `<s>` with one of `✓` / `✗` / `—` per the legend below; replace `<d>` with the per-check detail string.

Status values:

- `✓` — pass
- `✗` — fail
- `—` — skipped (only Check 5 can be skipped, per its dependency rules)

After the table, transition into Phase 2 by previewing the order of fixes. Example: "I'll offer to fix these in order: broker symlink, then permission, then version drift." This is a preview, **not** a single combined yes/no question. Regardless of how the user reacts to the preview, proceed into Phase 2 and ask each failing check individually with its own `y/n` prompt.

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
