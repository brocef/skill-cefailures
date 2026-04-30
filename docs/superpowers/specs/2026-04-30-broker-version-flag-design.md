# `broker --version` / `-V` flag

## Goal

Let users (and the user's agents) confirm which broker build they are running, so it is easy to tell when a `git pull` has actually swapped the broker behind the symlinked CLI.

## User-facing behavior

- Top-level flags `--version` and `-V` are added to the `broker` CLI.
- They are valid with no subcommand and no other arguments. They short-circuit before subcommand dispatch.
- On success: print a single line `broker {version}` to stdout (e.g. `broker 1.3.0`), exit 0.
- On failure to read the version: print nothing to stdout, write `broker: could not determine version` to stderr, exit 1.

There is no `version` subcommand, no per-subcommand version field, and no caching. The flag does only this.

## Source of truth

The version comes from `.claude-plugin/plugin.json` at the repo root. That file is already maintained by the project's existing release rhythm (bumped at release time, alongside `.claude-plugin/marketplace.json` and a matching `git tag`), so no new versioning train is introduced.

A consequence: any release bump moves the broker version, even if the broker code did not change. That is acceptable — the question this flag answers is "is my installed broker up to date with the latest cut?", and the plugin version answers exactly that.

## Resolution path

The `broker` CLI is normally invoked via a symlink (e.g. `~/.local/bin/broker -> .../scripts/broker_cli.py`). The version reader must follow the symlink back to the repo:

1. Start from `Path(__file__).resolve()` — `resolve()` chases the symlink, giving the real path of `broker_cli.py` inside `scripts/`.
2. Walk up one directory (`scripts/` → repo root).
3. Read `<repo-root>/.claude-plugin/plugin.json`, parse as JSON, return the `version` field as a string.

The version reflects the repo containing the resolved script file. If `broker_cli.py` is *copied* (rather than symlinked) outside the repo, or run from a checked-out worktree whose `plugin.json` differs from what the user thinks is installed, the helper will read whatever's at the resolved location — or hit the missing-file path and report failure. This is acceptable: symlink installs (the documented setup in `skills/broker/docs/setup.md`) work correctly; non-symlink installs are out of scope.

## Failure handling

The reader treats **any exception during read or parse** as "could not determine version", plus the schema check that `version` is a non-empty string. Concretely, this covers at least:

- `plugin.json` missing at the resolved path (`FileNotFoundError`)
- Permission denied on read (`PermissionError`)
- File is not valid UTF-8 / JSON (`UnicodeDecodeError`, `json.JSONDecodeError`)
- JSON object missing the `version` key, or `version` is not a string, or `version` is an empty string

In every failure case: stdout stays empty, stderr gets `broker: could not determine version`, exit code is 1. We deliberately do not echo the underlying error — the message tells the user what went wrong from their perspective; deeper diagnostics are not the job of `--version`.

## Implementation notes

- A new module-level helper `_read_plugin_version() -> str` lives in `scripts/broker_cli.py`, near the existing `DEFAULT_SOCKET` / `DEFAULT_STORAGE` constants. It raises a single internal exception class (or returns a sentinel) on any failure; the caller maps that to the stderr-message-and-exit-1 path.
- `argparse`'s built-in `action="version"` is **not** suitable. Python evaluates the `version=` keyword expression at the `add_argument` call site, so passing `version=_read_plugin_version()` would call the reader at parser-construction time. If the read fails, that crashes the entire CLI on every invocation — including `broker server`, `broker send`, etc. — not just `broker --version`.
- Instead, handle `--version` / `-V` with a custom argparse action whose `__call__` invokes `_read_plugin_version()`, prints the success line (or writes the stderr message) and calls `sys.exit(0 or 1)`. The action is added to the top-level parser in `main()` before subparsers are configured.
- The flag belongs to the top-level parser only, not to subparsers. `broker send --version` is not a supported invocation; argparse will reject it as an unknown flag for the `send` subcommand, which is the right behavior.

## Testing

One new test file (or new tests in an existing file) at `tests/test_broker_cli.py`:

1. **Success case (real symlink path):** in a `tmp_path`, lay out a fake repo (`<tmp>/.claude-plugin/plugin.json` with a known version, `<tmp>/scripts/broker_cli.py` copied or symlinked from the real one), then create a symlink `<tmp>/bin/broker` pointing at `<tmp>/scripts/broker_cli.py`. Invoke that symlink as a subprocess with `--version`. Assert stdout equals `broker {expected}\n`, stderr is empty, exit code is 0. Repeat the assertion for `-V`. This is the only test that actually exercises the `Path(__file__).resolve()` symlink-following behavior — the riskiest part of the resolution path.
2. **Failure cases:** drive `_read_plugin_version()` directly (with the resolution path pointed at a `tmp_path`) once per failure shape:
   - missing `plugin.json`
   - `plugin.json` exists but contains invalid JSON
   - `plugin.json` parses but is missing the `version` key
   - `plugin.json` has `version` set to a non-string (e.g. number)
   - `plugin.json` has `version` set to an empty string

   For each, assert the helper signals failure to the caller. Then add one end-to-end subprocess test for the missing-file case asserting exit 1, empty stdout, and stderr containing `broker: could not determine version` — that's enough to cover the CLI-level wiring.

Permission-error and decoding-error cases do not need dedicated tests; they share the same "any exception → failure" branch and would be redundant.

## Out of scope

- Embedding a separate `BROKER_VERSION` constant in `broker_constants.py`.
- Appending git SHA / build metadata to the output.
- Adding a `version` subcommand or a version field to any other command's output.
- Caching the version read across calls (each `--version` invocation is a fresh process; one file read per process is fine).
- Updating any documentation beyond release notes for the next version bump (the broker SKILL.md does not need to mention `--version`; it is self-evident from `broker --help`).
