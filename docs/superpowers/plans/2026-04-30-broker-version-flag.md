# `broker --version` / `-V` Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a top-level `--version` / `-V` flag to the `broker` CLI that prints `broker {version}` (read from `.claude-plugin/plugin.json`) and exits 0, or writes `broker: could not determine version` to stderr and exits 1 on failure.

**Architecture:** A pure helper `_read_plugin_version(repo_root)` reads and validates `<repo_root>/.claude-plugin/plugin.json`, raising `_VersionUnavailable` on any failure. A separate `_resolve_repo_root()` derives the repo root from the resolved script path so symlink installs (`~/.local/bin/broker`) work. A custom argparse action `_VersionAction` ties them together — invoked only when `--version`/`-V` is parsed, so a broken plugin.json never crashes unrelated subcommands at parser-build time.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `pathlib`), pytest.

**Spec:** [`docs/superpowers/specs/2026-04-30-broker-version-flag-design.md`](../specs/2026-04-30-broker-version-flag-design.md)

---

## File Map

- **Modify** `scripts/broker_cli.py` — add `_VersionUnavailable`, `_read_plugin_version()`, `_resolve_repo_root()`, `_VersionAction`, and wire the flag onto the top-level parser.
- **Modify** `tests/test_broker_cli.py` — add helper-level unit tests and CLI-level subprocess tests (including a real-symlink-chain integration test).
- **Modify** `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` — note the new flag.

No new files.

---

## Task 1: Helper happy path (TDD)

Add the `_read_plugin_version(repo_root)` helper and prove it reads a known version from a fake repo on disk.

**Files:**
- Modify: `tests/test_broker_cli.py` (add new test, no rewrites)
- Modify: `scripts/broker_cli.py` (add helper near `DEFAULT_SOCKET` / `DEFAULT_STORAGE` constants)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_cli.py`:

```python
# ---------------------------------------------------------------------------
# _read_plugin_version helper
# ---------------------------------------------------------------------------

def test_read_plugin_version_happy_path(tmp_path: Path) -> None:
    """_read_plugin_version reads the version field from plugin.json under repo_root."""
    from broker_cli import _read_plugin_version

    repo = tmp_path / "fake-repo"
    (repo / ".claude-plugin").mkdir(parents=True)
    (repo / ".claude-plugin" / "plugin.json").write_text(
        '{"version": "9.9.9", "name": "fake"}', encoding="utf-8",
    )

    assert _read_plugin_version(repo) == "9.9.9"
```

- [ ] **Step 2: Run the test, see it fail**

Run: `python -m pytest tests/test_broker_cli.py::test_read_plugin_version_happy_path -v`

Expected: FAIL with `ImportError` on `from broker_cli import _read_plugin_version` (the helper doesn't exist yet).

- [ ] **Step 3: Add the helper to `broker_cli.py`**

Insert immediately after the `DEFAULT_SOCKET` / `DEFAULT_STORAGE` constants (around line 562):

```python
def _read_plugin_version(repo_root: Path) -> str:
    """Read the version field from <repo_root>/.claude-plugin/plugin.json."""
    plugin_json = repo_root / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    return data["version"]
```

(Minimal — no error handling yet. Failure cases are added in Task 2.)

- [ ] **Step 4: Run the test, see it pass**

Run: `python -m pytest tests/test_broker_cli.py::test_read_plugin_version_happy_path -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker): add _read_plugin_version helper (happy path)"
```

---

## Task 2: Helper failure cases (TDD)

Cover every malformed-`plugin.json` shape from the spec by introducing `_VersionUnavailable` and broadening the helper to catch read/parse errors and validate the schema.

**Files:**
- Modify: `tests/test_broker_cli.py` (add a parametrized failure-case test)
- Modify: `scripts/broker_cli.py` (add exception class, harden helper)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_broker_cli.py`:

```python
@pytest.mark.parametrize(
    "label, write_content",
    [
        ("missing-file", None),
        ("invalid-json", "not json at all"),
        ("missing-version-key", '{"name": "fake"}'),
        ("non-string-version", '{"version": 1}'),
        ("empty-string-version", '{"version": ""}'),
    ],
)
def test_read_plugin_version_failures(
    tmp_path: Path, label: str, write_content: str | None,
) -> None:
    """Every malformed plugin.json shape raises _VersionUnavailable."""
    from broker_cli import _read_plugin_version, _VersionUnavailable

    repo = tmp_path / "fake-repo"
    (repo / ".claude-plugin").mkdir(parents=True)
    if write_content is not None:
        (repo / ".claude-plugin" / "plugin.json").write_text(
            write_content, encoding="utf-8",
        )

    with pytest.raises(_VersionUnavailable):
        _read_plugin_version(repo)
```

- [ ] **Step 2: Run the tests, see them fail**

Run: `python -m pytest tests/test_broker_cli.py::test_read_plugin_version_failures -v`

Expected: All five parametrizations FAIL — `_VersionUnavailable` doesn't exist yet, and the current helper raises `FileNotFoundError`, `json.JSONDecodeError`, or `KeyError` instead of `_VersionUnavailable`.

- [ ] **Step 3: Add the exception class**

In `broker_cli.py`, immediately above `_read_plugin_version`:

```python
class _VersionUnavailable(Exception):
    """Raised when plugin.json cannot be read, parsed, or validated."""
```

- [ ] **Step 4: Harden the helper**

Replace the body of `_read_plugin_version` with:

```python
def _read_plugin_version(repo_root: Path) -> str:
    """Read the version field from <repo_root>/.claude-plugin/plugin.json.

    Raises _VersionUnavailable on any read, parse, or schema failure. The
    underlying error is chained via __cause__ for debuggers but is not surfaced
    to the user.
    """
    plugin_json = repo_root / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _VersionUnavailable() from exc
    if not isinstance(data, dict):
        raise _VersionUnavailable()
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise _VersionUnavailable()
    return version
```

`OSError` covers `FileNotFoundError` and `PermissionError`; `ValueError` covers `json.JSONDecodeError` and `UnicodeDecodeError` (both are `ValueError` subclasses). This matches the spec's "any exception during read or parse" stance with a slightly tighter catch than bare `Exception`.

- [ ] **Step 5: Run the tests, see them pass**

Run: `python -m pytest tests/test_broker_cli.py::test_read_plugin_version_happy_path tests/test_broker_cli.py::test_read_plugin_version_failures -v`

Expected: All six tests PASS (1 happy path + 5 parametrized failure shapes).

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker): handle malformed plugin.json in _read_plugin_version"
```

---

## Task 3: Wire `--version` / `-V` onto the CLI (TDD with subprocess tests)

Add `_resolve_repo_root()` and the custom `_VersionAction`, register the flag on the top-level parser, and prove the end-to-end behavior with subprocess tests — including a real-symlink-chain test that exercises the `Path(__file__).resolve()` resolution path.

**Files:**
- Modify: `tests/test_broker_cli.py` (add CLI-level tests)
- Modify: `scripts/broker_cli.py` (add `_resolve_repo_root`, `_VersionAction`, parser registration)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_broker_cli.py`. Note: `BROKER_CLI` is already defined at the top of the file; reuse it.

```python
# ---------------------------------------------------------------------------
# --version / -V CLI flag
# ---------------------------------------------------------------------------

def _expected_version_from_repo() -> str:
    plugin_json = Path(__file__).parent.parent / ".claude-plugin" / "plugin.json"
    return json.loads(plugin_json.read_text(encoding="utf-8"))["version"]


def test_version_flag_long() -> None:
    """`broker --version` reads .claude-plugin/plugin.json and prints `broker {version}`."""
    expected = _expected_version_from_repo()
    result = subprocess.run(
        [sys.executable, BROKER_CLI, "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"broker {expected}\n"
    assert result.stderr == ""


def test_version_flag_short() -> None:
    """`broker -V` is an alias for `--version`."""
    expected = _expected_version_from_repo()
    result = subprocess.run(
        [sys.executable, BROKER_CLI, "-V"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"broker {expected}\n"
    assert result.stderr == ""


def _build_fake_repo_with_symlink(tmp_path: Path, plugin_version: str | None) -> Path:
    """Lay out <tmp>/fake-repo/{scripts,.claude-plugin}/ + a bin/broker symlink.

    Returns the path to the bin/broker symlink. Set plugin_version=None to skip
    creating plugin.json (forces the missing-file failure path).
    """
    import shutil
    fake_repo = tmp_path / "fake-repo"
    fake_scripts = fake_repo / "scripts"
    real_scripts = Path(__file__).parent.parent / "scripts"
    # Copy the entire scripts/ tree so broker_cli.py can import its siblings.
    shutil.copytree(real_scripts, fake_scripts)
    if plugin_version is not None:
        (fake_repo / ".claude-plugin").mkdir()
        (fake_repo / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"version": plugin_version}), encoding="utf-8",
        )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    bin_link = bin_dir / "broker"
    bin_link.symlink_to(fake_scripts / "broker_cli.py")
    return bin_link


def test_version_flag_via_symlink_chain(tmp_path: Path) -> None:
    """Invoking `broker --version` via a bin/-symlink reads plugin.json from the
    resolved repo root, not from the original install location."""
    bin_link = _build_fake_repo_with_symlink(tmp_path, plugin_version="9.9.9")
    result = subprocess.run(
        [sys.executable, str(bin_link), "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "broker 9.9.9\n"
    assert result.stderr == ""


def test_version_flag_missing_plugin_json(tmp_path: Path) -> None:
    """If plugin.json is absent, exit 1 with the canned stderr message and empty stdout."""
    bin_link = _build_fake_repo_with_symlink(tmp_path, plugin_version=None)
    result = subprocess.run(
        [sys.executable, str(bin_link), "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "broker: could not determine version" in result.stderr
```

- [ ] **Step 2: Run the tests, see them fail**

Run: `python -m pytest tests/test_broker_cli.py -v -k version_flag`

Expected: All four CLI tests FAIL — `--version` and `-V` are unrecognized arguments, so argparse exits 2 with a usage error on stderr.

- [ ] **Step 3: Add `_resolve_repo_root` and `_VersionAction` to `broker_cli.py`**

Insert immediately after `_read_plugin_version` (and before `def main()`):

```python
def _resolve_repo_root() -> Path:
    """Walk from the resolved script path up one directory to the repo root.

    Path(__file__).resolve() chases the install symlink (e.g. ~/.local/bin/broker
    -> .../scripts/broker_cli.py), landing on the real script file inside the
    repo's scripts/ directory. The parent of that is the repo root.
    """
    return Path(__file__).resolve().parent.parent


class _VersionAction(argparse.Action):
    """Print `broker {version}` and exit. Reads plugin.json on demand.

    Defined as a custom action (rather than argparse's built-in
    action="version") because Python evaluates the version= keyword expression
    at add_argument call time. Calling _read_plugin_version() inline there
    would crash every CLI invocation — including unrelated subcommands — if
    plugin.json is unreadable. This action defers the read to flag-parse time.
    """

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: str = argparse.SUPPRESS,
        help: str = "Print broker version and exit",
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        try:
            version = _read_plugin_version(_resolve_repo_root())
        except _VersionUnavailable:
            print("broker: could not determine version", file=sys.stderr)
            sys.exit(1)
        print(f"broker {version}")
        sys.exit(0)
```

- [ ] **Step 4: Register the flag on the top-level parser**

In `main()`, locate the existing parser construction (around line 567):

```python
    parser = argparse.ArgumentParser(
        description="Message broker for multi-agent conversations"
    )
    subparsers = parser.add_subparsers(dest="command")
```

Insert one line between those two so the flag is added to the top-level parser before subparsers are configured:

```python
    parser = argparse.ArgumentParser(
        description="Message broker for multi-agent conversations"
    )
    parser.add_argument("-V", "--version", action=_VersionAction)
    subparsers = parser.add_subparsers(dest="command")
```

- [ ] **Step 5: Run the new tests, see them pass**

Run: `python -m pytest tests/test_broker_cli.py -v -k version_flag`

Expected: All four version-flag tests PASS.

- [ ] **Step 6: Run the full test file to confirm no regressions**

Run: `python -m pytest tests/test_broker_cli.py -v`

Expected: All tests PASS, including pre-existing tests like `test_help_flag` (the `-V` short option does not collide with anything else).

- [ ] **Step 7: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker): add --version/-V flag"
```

---

## Task 4: Release notes and changelog

The project's CLAUDE.md requires `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` to track unreleased changes. Both are currently empty (just a `# Upcoming` header).

**Files:**
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`

- [ ] **Step 1: Add the changelog entry**

Replace the contents of `docs/changelogs/upcoming.md` with:

```markdown
# Upcoming

## Added
- `broker --version` / `broker -V` — print the installed broker version (read from `.claude-plugin/plugin.json`) and exit. Exits non-zero with `broker: could not determine version` on stderr if plugin.json is missing or malformed.
```

- [ ] **Step 2: Add the release-note entry**

Replace the contents of `docs/release-notes/upcoming.md` with:

```markdown
# Upcoming

## Broker

The `broker` CLI now supports `--version` / `-V`. Run `broker --version` to confirm which build you have installed — useful for telling whether a `git pull` actually swapped the broker behind your `~/.local/bin/broker` symlink. The version is read from the plugin's `plugin.json` at the resolved script location, so it always reflects the running code.
```

- [ ] **Step 3: Commit**

```bash
git add docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "docs(broker): note --version/-V flag in upcoming notes"
```

---

## Task 5: Manual smoke test

A subprocess-based test suite covers most of the surface, but verify by hand that the `~/.local/bin/broker` symlink the user actually uses prints the right thing.

**Files:** none (manual verification only).

- [ ] **Step 1: Print the version via the install symlink**

Run: `broker --version`

Expected output: `broker 1.3.0` (or whatever value is in `.claude-plugin/plugin.json` at the time of execution), exit code 0.

- [ ] **Step 2: Confirm the short flag**

Run: `broker -V`

Expected: identical output to Step 1, exit code 0.

- [ ] **Step 3: Confirm `--help` lists the flag**

Run: `broker --help`

Expected: the top-level help text includes a `-V`, `--version` line under the "options" section, in addition to the existing subcommand list.

- [ ] **Step 4: Confirm subcommand parsers still work**

Run: `broker whoami`

Expected: prints the cwd-derived identity, unchanged from before.

If any of these fail, return to the prior task.

---

## Final Verification

- [ ] Run the full test suite: `python -m pytest tests/ -v`. Expected: all tests pass.
- [ ] Run `broker --version` from the install symlink one last time. Expected: matches `.claude-plugin/plugin.json`.
- [ ] `git log --oneline` shows four commits (one per code task plus the docs commit), in order: helper happy path → helper failure cases → CLI flag wiring → release-notes update.
