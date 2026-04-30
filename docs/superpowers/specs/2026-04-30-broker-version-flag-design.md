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

## Failure handling

The reader treats any of the following as "could not determine version":

- `plugin.json` missing at the resolved path
- File present but not valid JSON
- JSON object missing the `version` key, or `version` is not a string

In every failure case: stdout stays empty, stderr gets `broker: could not determine version`, exit code is 1. We deliberately do not echo the underlying error (file-not-found, JSON parse error, etc.) — the message tells the user what went wrong from their perspective; deeper diagnostics are not the job of `--version`.

## Implementation notes

- A new module-level helper `_read_plugin_version() -> str` lives in `scripts/broker_cli.py`, near the existing `DEFAULT_SOCKET` / `DEFAULT_STORAGE` constants. It raises a single internal exception class (or returns a sentinel) on any failure; the caller maps that to the stderr-message-and-exit-1 path.
- `argparse`'s built-in `action="version"` is **not** suitable, because it evaluates the version string eagerly when the argument is added to the parser. If the read fails, that would crash the entire CLI on every invocation — including `broker server`, `broker send`, etc. — not just `broker --version`.
- Instead, handle `--version` / `-V` with a custom argparse action whose `__call__` invokes `_read_plugin_version()`, prints the success line (or writes the stderr message) and calls `sys.exit(0 or 1)`. The action is added to the top-level parser in `main()` before subparsers are configured.
- The flag belongs to the top-level parser only, not to subparsers. `broker send --version` is not a supported invocation; argparse will reject it as an unknown flag for the `send` subcommand, which is the right behavior.

## Testing

One new test file (or new tests in an existing file) at `tests/test_broker_cli.py`:

1. **Success case:** read the expected version directly from `.claude-plugin/plugin.json`, invoke the broker CLI as a subprocess with `--version`, assert stdout equals `broker {expected}\n`, stderr is empty, exit code is 0. Repeat for `-V`.
2. **Failure case:** invoke `_read_plugin_version()` (or the CLI) with a working directory / `__file__` arrangement where `plugin.json` is missing or malformed. Assert exit 1, empty stdout, stderr contains `broker: could not determine version`. Easiest setup: monkeypatch the helper's resolution path to point at a `tmp_path` that does not contain `plugin.json`, and at one that contains a JSON file with no `version` key.

No need to test every shape of malformed JSON — one missing-file case and one missing-key case is enough to cover the failure branch.

## Out of scope

- Embedding a separate `BROKER_VERSION` constant in `broker_constants.py`.
- Appending git SHA / build metadata to the output.
- Adding a `version` subcommand or a version field to any other command's output.
- Caching the version read across calls (each `--version` invocation is a fresh process; one file read per process is fine).
- Updating any documentation beyond release notes for the next version bump (the broker SKILL.md does not need to mention `--version`; it is self-evident from `broker --help`).
