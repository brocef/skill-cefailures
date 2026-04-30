# Broker Health Check

## Goal

Give the user a way to ask Claude "is my broker setup OK?" and get a concrete answer — and an offer to fix anything that isn't. Targets the friction points that keep coming up: a missing or stale install symlink, a server that isn't running, a missing permission rule, or a version mismatch after a plugin upgrade.

## Form factor and invocation

A new doc page at `skills/broker/docs/health-check.md` referenced from the broker `SKILL.md`. Claude reads it when the user says things like:

- "check broker setup"
- "is broker working / healthy"
- "diagnose broker"
- "broker doctor"
- "what's wrong with broker"

It is not a slash command and not a `broker` subcommand. Invocation is via natural language; the SKILL.md routing layer is what tells Claude when to load `docs/health-check.md`.

## Two phases

The doc instructs Claude to run a strict diagnose-then-remediate sequence: never offer fixes during the diagnose phase, never re-run diagnostics during the remediate phase.

### Phase 1 — Diagnose

Run all five checks below, then print one summary table of results. No action taken on failures yet.

| # | Check | Pass criteria | Detail on fail |
|---|-------|---------------|----------------|
| 1 | `~/.local/bin` on `$PATH` | `case ":$PATH:" in *":$HOME/.local/bin:"*) echo ok;; esac` matches | "not on PATH" |
| 2 | `broker` symlink valid | `test -L ~/.local/bin/broker` AND `readlink -f ~/.local/bin/broker` resolves to a readable file ending in `broker_cli.py` | "missing" or "dangling: <path>" or "wrong target: <path>" |
| 3 | broker server reachable | `test -S ~/.mcp-broker/broker.sock` (file existence only — no round-trip) | "no socket at ~/.mcp-broker/broker.sock" |
| 4 | `Bash(broker:*)` permission active | At least one entry in `permissions.allow[]` starts with `Bash(broker:` in any of: `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json` | "not found in project or user settings" |
| 5 | broker version matches plugin cache | `broker --version` parses as `broker X.Y.Z`. If the resolved symlink target is under `~/.claude/plugins/cache/`, find the highest-versioned plugin cache dir for `skill-cefailures` and read its `plugin.json`; compare `version` strings. | `1.3.0 ≠ 1.3.1 (stale symlink — points at older cached plugin)`. If the resolved target is NOT under the plugin cache (e.g. dev symlink to a checked-out repo), report the broker version and explicitly skip the comparison: "drift check skipped (dev install at <path>)". |

The summary table format:

```
| Check                          | Status | Detail                              |
|--------------------------------|:------:|-------------------------------------|
| ~/.local/bin on $PATH          |   ✓    | matched $PATH segment               |
| broker symlink valid           |   ✗    | missing                             |
| broker server reachable        |   ✗    | no socket at ~/.mcp-broker/broker.sock |
| Bash(broker:*) permission      |   ✓    | found in ~/.claude/settings.json    |
| broker version matches plugin  |   —    | depends on check 2 (symlink)        |
```

`—` (em dash) is reserved for checks that were skipped because a prerequisite failed. The dependency chain Claude must enforce:

- Check 5 (version drift) depends on Check 2 (symlink). If Check 2 fails, Check 5 is `—` with detail `depends on check 2 (symlink)`.
- A separate `—` case for Check 5: the symlink is valid (Check 2 passed) but the resolved target is not under `~/.claude/plugins/cache/`. In that case the detail is `dev install at <resolved-path>` (a passing skip, not a dependency skip).

No other dependency cascades exist. Checks 1, 3, and 4 are independent.

### Phase 2 — Remediate

For each ✗ in the table, ask "Fix [name]? (y/n)" and run the per-check remediation on yes. Order is fixed: PATH → symlink → permission → server → version drift. The ordering reflects dependency, not cost: PATH must exist before the symlink is reachable; the symlink must exist before any `broker` invocation works; the permission must be granted before Claude itself can call `broker` later in the session without a prompt; the server is user-action so it follows the Claude-actionable items; version drift is a downstream effect of a stale symlink so it's last.

Per-check remediation:

1. **PATH.** Print the exact `export PATH="$HOME/.local/bin:$PATH"` line and tell the user which shell rc file to add it to (`.zshrc` / `.bashrc` based on `$SHELL` if detectable, else neutral phrasing). **Do not edit shell rc files.** Too many shells, too many setups. After printing, mark the fix as "user action required" — do not re-verify in Phase 1; the user must restart their shell.
2. **Symlink.** Run `mkdir -p ~/.local/bin && ln -sf <target> ~/.local/bin/broker`. The `<target>` is resolved by finding the highest-versioned cache dir at `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/<version>/scripts/broker_cli.py`. If no plugin cache exists (dev install case), Claude asks the user for the absolute path and records that they're on a dev install.
3. **Permission.** Invoke the existing `update-config` skill to add `Bash(broker:*)` to `permissions.allow[]`. Claude asks first whether to add to project (`.claude/settings.json`) or user (`~/.claude/settings.json`) settings — default suggestion: project.
4. **Server.** Print the command `broker server` and tell the user to run it in another terminal (foreground, so they can see logs and Ctrl-C it). **Do not start the server from inside Claude.** After printing, mark as "user action required."
5. **Version drift.** Re-run remediation 2 (symlink). The drift is always caused by a stale symlink pointing at an older cache dir.

After all yes-fixes complete, Claude prints a one-line summary: "X of Y issues fixed; Z still require user action (PATH / server)."

## Permission detection details

For check 4, scan in this order; first hit wins (and is reported):

1. `<cwd>/.claude/settings.local.json` — highest precedence project-local override.
2. `<cwd>/.claude/settings.json` — committed project settings.
3. `~/.claude/settings.json` — user-global.

In each file, look at `permissions.allow` (an array of strings). Pass if any entry starts with `Bash(broker:` (so `Bash(broker:*)`, `Bash(broker:read)`, `Bash(broker:send,broker:read)` all count). If none match, report "not found in project or user settings." Don't bother with `permissions.deny` — its presence wouldn't change Phase-1 conclusions, and Phase-2 remediation always adds `Bash(broker:*)` to `allow`.

If a settings file exists but is not valid JSON, treat it as if the file did not exist for matching purposes, but flag it in the table's Detail column ("settings.json malformed — skipped").

## Version-drift detection details

For check 5:

1. Run `broker --version`. Parse the line as `broker {version}`. If the command fails (exit non-zero, or output doesn't match), the check fails with "broker --version failed: <stderr first line>".
2. Resolve the broker symlink with `readlink -f ~/.local/bin/broker`. If the resolved path matches the regex `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/[^/]+/scripts/broker_cli.py`, extract the version segment and the plugin cache dir.
3. List sibling version dirs at `~/.claude/plugins/cache/skill-cefailures/skill-cefailures/`. The "expected" version is the lexicographically highest entry (good enough for semver patch differences; the corner case where `1.10.0` < `1.9.0` lexicographically can be addressed in a future iteration if the project ever hits double-digit minors).
4. Compare. If equal: pass. If different: fail with `running 1.3.0 ≠ latest cached 1.3.1 (stale symlink)`.
5. If step 2's regex does not match (the symlink points elsewhere), skip the comparison. Report `drift check skipped (dev install at <resolved-path>)` and pass with a `—` status.

## SKILL.md changes

Two edits to `skills/broker/SKILL.md`:

1. Add a row to the Docs table at the bottom:

   | `docs/health-check.md` | Diagnose setup; offer to fix issues — read when the user says "is broker working", "broker doctor", "diagnose broker", or similar |

2. Add one line to the Prerequisites section just under the existing two bullets:

   - Run `broker doctor`-style diagnostics by asking Claude to "check broker setup" — see `docs/health-check.md`.

(Note: `broker doctor` is not an actual subcommand. The line is phrasing for Claude to suggest the natural-language invocation.)

## Out of scope

- Editing the user's shell rc files (`.bashrc` / `.zshrc` / `config.fish` / etc.).
- Auto-starting `broker server` from inside Claude (background or otherwise).
- Token-file / reserved-identity sanity checks.
- Multi-version cleanup of stale plugin cache directories.
- A `broker doctor` CLI subcommand. The health check is doc-driven; if a CLI subcommand becomes valuable later, it gets its own design.
- Automated tests of the doc itself. The implementation plan should specify a manual hand-test (run a Claude session with each failure mode artificially induced and confirm Claude produces the expected table and remediation flow).

## Non-goals worth naming

- This is not a continuous monitor. It runs once when invoked, reports, and exits.
- It does not warn about deprecated subcommands (`broker create`/`join`/`leave` still emit their own warnings).
- It does not check whether *other* agents on the broker are reachable or have valid identity tokens. Its scope is the local install only.
