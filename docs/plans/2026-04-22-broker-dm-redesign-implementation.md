# Broker DM-only redesign — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broker's room-based model with a pure DM / store-and-forward inbox model, while keeping room APIs operational during the transition.

**Architecture:** Server gains per-identity inbox + outbox log files (newline-delimited display-format lines, durable on disk), a small identity registry, and reserved-identity enforcement. CLI gains `send --to`, `broadcast`, `reply-all`, `history`, and a `follow` that tails the inbox log from a byte-offset cursor. Identity is derived client-side from `package.json` or `<org>/<repo>` so senders compute recipients without a directory service. Room APIs remain but emit deprecation warnings.

**Tech Stack:** Python 3, asyncio, Unix domain sockets, pytest. No new external dependencies.

**Source:** Design doc at `docs/plans/2026-04-22-broker-dm-redesign-design.md`.

---

## Resolved open questions (committed defaults for this plan)

These four items were left open in the design doc. The plan commits to these defaults; revisit if implementation surfaces problems.

1. **Registration model.** Implicit. An identity is considered registered the first time the server sees a request from it (`send`, `broadcast`, `follow`, `history`, `read`). Derivation is enforced *client-side* in the CLI: if `--identity` is not provided, the CLI computes it from the cwd; if provided, the CLI trusts it. Reserved identities (`orchestrator`, `human`, `BROADCAST`) are enforced *server-side* at registration via per-host token files at `~/.mcp-broker/tokens/<identity>.token`. Server maintains an identity registry at `~/.mcp-broker/identities.json` tracking `firstSeenAt` / `lastSeenAt` / `lastWriteAt`.

2. **Broker scoping.** Per-host, matching today's `~/.mcp-broker/broker.sock`. `orchestrator` and `human` are singletons per broker instance. Users running multiple concurrent workspaces who need distinct orchestrators must use scoped identities (e.g., `orchestrator:proposit-app`). `broker whoami` prints the derived identity + cwd so collisions are debuggable.

3. **`follow` stream mechanism.** Server appends each delivered message to `~/.mcp-broker/inbox/<encoded-identity>.log` (one line per message in the display format, content newlines escaped as `\\n`). `broker follow` tails the file from the identity's byte-offset cursor at `~/.mcp-broker/cursors/<encoded-identity>.cursor`, drains to EOF, advances the cursor, and then blocks reading further appended lines. The Claude Code `Monitor` tool can tail the same file independently.

4. **Sent-message visibility.** Server also appends every outgoing message to `~/.mcp-broker/outbox/<encoded-identity>.log`. `broker history --sent` reads from outbox instead of inbox. Retention: forever for this plan; rotation is out of scope.

---

## File structure

### New files

```
scripts/
  broker_identity.py        # Identity derivation from package.json / git
  broker_storage.py         # InboxLog, OutboxLog, CursorStore, IdentityRegistry
  broker_format.py          # format_message / parse_message / escape helpers
  broker_constants.py       # BROADCAST sentinel, RESERVED_IDENTITIES set
tests/
  test_broker_identity.py
  test_broker_storage.py
  test_broker_format.py
  test_broker_dm_server.py  # DM-only server request tests
  test_broker_dm_cli.py     # DM-only CLI end-to-end tests
```

### Modified files

```
scripts/broker_server.py    # Add DM handlers alongside room handlers
scripts/broker_client.py    # Add DM methods
scripts/broker_cli.py       # Add send/broadcast/reply-all/history/follow subcommands; default --identity via derivation
skills/broker/SKILL.md      # Rewrite for DM model
skills/broker/docs/usage.md
skills/broker/docs/patterns.md
skills/broker/docs/troubleshooting.md
skills/broker/docs/signals.md
skills/broker/docs/setup.md
docs/release-notes/upcoming.md
docs/changelogs/upcoming.md
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
```

### File responsibilities

| File | Responsibility |
|---|---|
| `broker_identity.py` | Compute deterministic identity from cwd. Pure function, no I/O beyond file reads. |
| `broker_storage.py` | All on-disk structures: inbox/outbox log append + line-offset read, byte-offset cursor, identity registry JSON. Atomic operations, no async. |
| `broker_format.py` | Encode/decode the display-format line. Escape/unescape newlines and backslashes in content. |
| `broker_constants.py` | `BROADCAST = "BROADCAST"`; `RESERVED_IDENTITIES = {"orchestrator", "human", "BROADCAST"}`. |
| `broker_server.py` | Dispatch DM requests to storage. Enforce reserved identities. Look up reply-all recipient sets. |
| `broker_client.py` | Thin async client methods that wrap new server request types. |
| `broker_cli.py` | argparse subcommands; default `--identity` via `derive_identity(cwd)`; `follow` tails inbox log. |

---

## Task list

- Phase 1: Primitives (T1–T6)
- Phase 2: Server DM handlers (T7–T12)
- Phase 3: Client + CLI (T13–T21)
- Phase 4: Migration glue + integration test (T22–T23)
- Phase 5: Skill rewrite (T24–T29)
- Phase 6: Release (T30–T31)

Every task follows TDD: write failing test → run → implement → run → commit.

---

## Phase 1: Primitives

### Task 1: Identity derivation

**Files:**
- Create: `scripts/broker_identity.py`
- Test: `tests/test_broker_identity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broker_identity.py
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_identity import derive_identity, IdentityDerivationError


def test_package_json_name_wins(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "@scope/pkg"}))
    assert derive_identity(tmp_path) == "@scope/pkg"


def test_package_json_unscoped(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "proposit-server"}))
    assert derive_identity(tmp_path) == "proposit-server"


def test_package_json_missing_name_falls_through_to_git(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"version": "1.0.0"}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:Proposit-App/proposit-mobile.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Proposit-App/proposit-mobile"


def test_git_remote_https_url(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/Proposit-App/proposit-core.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Proposit-App/proposit-core"


def test_no_package_no_git_raises(tmp_path: Path) -> None:
    with pytest.raises(IdentityDerivationError):
        derive_identity(tmp_path)


def test_nearest_package_json_from_subdir(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "outer"}))
    inner = tmp_path / "pkg"
    inner.mkdir()
    (inner / "package.json").write_text(json.dumps({"name": "inner"}))
    assert derive_identity(inner) == "inner"


def test_walks_up_to_find_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "root"}))
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert derive_identity(deep) == "root"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_identity.py -v`
Expected: all fail with `ModuleNotFoundError: No module named 'broker_identity'`.

- [ ] **Step 3: Implement `broker_identity.py`**

```python
#!/usr/bin/env python3
"""Derive a stable identity string from a working directory."""

import json
import re
import subprocess
from pathlib import Path


class IdentityDerivationError(ValueError):
    """Raised when no identity can be derived from the cwd."""


def _find_nearest_package_json(start: Path) -> Path | None:
    """Walk up from `start` to find the nearest package.json. Returns None if none found."""
    current = start.resolve()
    while True:
        candidate = current / "package.json"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _identity_from_package_json(pkg_path: Path) -> str | None:
    """Return the package name, or None if missing/empty."""
    try:
        data = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        return name
    return None


def _identity_from_git_remote(cwd: Path) -> str | None:
    """Parse `git remote get-url origin` into `<org>/<repo>`, or None."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    url = result.stdout.strip()
    # Matches git@github.com:Org/Repo.git and https://github.com/Org/Repo(.git)
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def derive_identity(cwd: Path) -> str:
    """Compute the canonical identity for an agent running at `cwd`.

    Rules (in order):
      1. Nearest `package.json` going up; if its `name` field is a non-empty string, use it verbatim.
      2. Otherwise, parse `git remote get-url origin` into `<org>/<repo>`.
      3. Otherwise, raise `IdentityDerivationError`.
    """
    pkg = _find_nearest_package_json(cwd)
    if pkg is not None:
        name = _identity_from_package_json(pkg)
        if name is not None:
            return name
    remote = _identity_from_git_remote(cwd)
    if remote is not None:
        return remote
    raise IdentityDerivationError(
        f"Cannot derive identity from {cwd}: no package.json with name, no git remote origin."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_identity.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_identity.py tests/test_broker_identity.py
git commit -m "feat(broker): derive_identity() from package.json or git remote"
```

---

### Task 2: Message format + escape helpers

**Files:**
- Create: `scripts/broker_format.py`
- Test: `tests/test_broker_format.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broker_format.py
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_format import (
    escape_content,
    unescape_content,
    format_message,
    parse_message,
    ParsedMessage,
)


def test_escape_newlines_and_backslashes() -> None:
    assert escape_content("hello\nworld") == "hello\\nworld"
    assert escape_content("a\\b") == "a\\\\b"
    assert escape_content("a\\nb") == "a\\\\nb"


def test_unescape_is_inverse() -> None:
    originals = ["plain", "two\nlines", "back\\slash", "mixed\\n\\\\\n"]
    for s in originals:
        assert unescape_content(escape_content(s)) == s


def test_format_single_recipient_omits_arrow() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="@proposit/shared",
        recipients=["proposit-server"],
        content="CI green",
        viewer="proposit-server",
    )
    assert line == "2026-04-22T17:30:00Z [@proposit/shared] CI green"


def test_format_multi_recipient_shows_arrow_with_you_alias() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="proposit-mobile",
        recipients=["@proposit/shared", "proposit-server"],
        content="bumped to 0.3.0",
        viewer="@proposit/shared",
    )
    assert line == "2026-04-22T17:30:00Z [proposit-mobile → you, proposit-server] bumped to 0.3.0"


def test_format_broadcast() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="@proposit/shared",
        recipients=["BROADCAST"],
        content="publishing now",
        viewer="proposit-server",
    )
    assert line == "2026-04-22T17:30:00Z [@proposit/shared → BROADCAST] publishing now"


def test_format_escapes_newlines_in_content() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="a",
        recipients=["b"],
        content="line1\nline2",
        viewer="b",
    )
    assert "\n" not in line
    assert line.endswith("line1\\nline2")


def test_parse_single_recipient() -> None:
    parsed = parse_message("2026-04-22T17:30:00Z [alice] hi there", viewer="bob")
    assert parsed == ParsedMessage(
        timestamp="2026-04-22T17:30:00Z",
        sender="alice",
        recipients=["bob"],
        is_broadcast=False,
        content="hi there",
    )


def test_parse_multi_recipient_with_you() -> None:
    parsed = parse_message(
        "2026-04-22T17:30:00Z [mobile → you, server] bumped 0.3.0", viewer="shared"
    )
    assert parsed.sender == "mobile"
    assert parsed.recipients == ["shared", "server"]
    assert parsed.is_broadcast is False
    assert parsed.content == "bumped 0.3.0"


def test_parse_broadcast() -> None:
    parsed = parse_message(
        "2026-04-22T17:30:00Z [shared → BROADCAST] publishing now", viewer="mobile"
    )
    assert parsed.is_broadcast is True
    assert parsed.recipients == ["BROADCAST"]
    assert parsed.sender == "shared"


def test_parse_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        parse_message("not a message line", viewer="x")


def test_parse_unescapes_content() -> None:
    parsed = parse_message("2026-04-22T17:30:00Z [a] line1\\nline2", viewer="b")
    assert parsed.content == "line1\nline2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_format.py -v`
Expected: all fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `broker_format.py`**

```python
#!/usr/bin/env python3
"""Line-oriented message display format for the DM broker.

    <ISO8601> [<sender>] <content>                                 # single recipient (inbox context)
    <ISO8601> [<sender> → <recipient>, <recipient>] <content>      # multi-recipient; viewer appears as 'you'
    <ISO8601> [<sender> → BROADCAST] <content>                     # broadcast
"""

import re
from dataclasses import dataclass


_LINE_RE = re.compile(r"^(\S+)\s+\[([^\]]+)\]\s+(.*)$")


@dataclass
class ParsedMessage:
    timestamp: str
    sender: str
    recipients: list[str]
    is_broadcast: bool
    content: str


def escape_content(content: str) -> str:
    """Encode a message body so it fits on one line. Backslashes first, then newlines."""
    return content.replace("\\", "\\\\").replace("\n", "\\n")


def unescape_content(escaped: str) -> str:
    """Inverse of escape_content. Decodes `\\n` → newline and `\\\\` → `\\`."""
    result = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch == "\\" and i + 1 < len(escaped):
            nxt = escaped[i + 1]
            if nxt == "n":
                result.append("\n")
                i += 2
                continue
            if nxt == "\\":
                result.append("\\")
                i += 2
                continue
        result.append(ch)
        i += 1
    return "".join(result)


def format_message(
    timestamp: str,
    sender: str,
    recipients: list[str],
    content: str,
    viewer: str,
) -> str:
    """Render a message as a single display line for the given viewer.

    Single-recipient messages (where the viewer is the sole recipient) omit the arrow.
    Multi-recipient messages list all recipients, substituting `you` for the viewer.
    Broadcasts render the literal `BROADCAST` token.
    """
    escaped = escape_content(content)
    if recipients == ["BROADCAST"]:
        return f"{timestamp} [{sender} → BROADCAST] {escaped}"
    if len(recipients) == 1 and recipients[0] == viewer:
        return f"{timestamp} [{sender}] {escaped}"
    rendered = [("you" if r == viewer else r) for r in recipients]
    return f"{timestamp} [{sender} → {', '.join(rendered)}] {escaped}"


def parse_message(line: str, viewer: str) -> ParsedMessage:
    """Parse a display line back into its components. `viewer` resolves the `you` alias."""
    match = _LINE_RE.match(line)
    if not match:
        raise ValueError(f"Malformed message line: {line!r}")
    timestamp, meta, raw_content = match.group(1), match.group(2), match.group(3)
    content = unescape_content(raw_content)
    if " → " in meta:
        sender, recipient_part = meta.split(" → ", 1)
        if recipient_part == "BROADCAST":
            return ParsedMessage(timestamp, sender, ["BROADCAST"], True, content)
        recipients = [r.strip() for r in recipient_part.split(",")]
        recipients = [viewer if r == "you" else r for r in recipients]
        return ParsedMessage(timestamp, sender, recipients, False, content)
    # No arrow → viewer is the sole recipient
    return ParsedMessage(timestamp, meta, [viewer], False, content)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_format.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_format.py tests/test_broker_format.py
git commit -m "feat(broker): display-format encoder/decoder with newline escaping"
```

---

### Task 3: Constants (reserved identities, sentinel)

**Files:**
- Create: `scripts/broker_constants.py`

- [ ] **Step 1: Write the file**

```python
#!/usr/bin/env python3
"""Cross-module constants for the DM broker."""

BROADCAST = "BROADCAST"

RESERVED_IDENTITIES: frozenset[str] = frozenset({
    "orchestrator",
    "human",
    "BROADCAST",
})
```

- [ ] **Step 2: Commit**

```bash
git add scripts/broker_constants.py
git commit -m "feat(broker): define BROADCAST sentinel and reserved identities"
```

---

### Task 4: Storage primitives (inbox, outbox, cursor, registry)

**Files:**
- Create: `scripts/broker_storage.py`
- Test: `tests/test_broker_storage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broker_storage.py
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_storage import (
    InboxLog,
    OutboxLog,
    CursorStore,
    IdentityRegistry,
    encode_identity,
)


def test_encode_identity_replaces_slash() -> None:
    assert encode_identity("@proposit/shared") == "@proposit_shared"
    assert encode_identity("Proposit-App/proposit-mobile") == "Proposit-App_proposit-mobile"
    assert encode_identity("plain") == "plain"


def test_inbox_append_reads_back(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "line one")
    log.append("alice", "line two")
    assert log.path_for("alice").read_text() == "line one\nline two\n"


def test_inbox_read_from_offset(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "one")
    log.append("alice", "two")
    log.append("alice", "three")
    first_line_end = len("one\n")
    lines, new_offset = log.read_from("alice", offset=first_line_end)
    assert lines == ["two", "three"]
    assert new_offset == len("one\ntwo\nthree\n")


def test_inbox_read_empty_for_unknown_identity(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    lines, offset = log.read_from("nobody", offset=0)
    assert lines == []
    assert offset == 0


def test_inbox_partial_trailing_line_not_returned(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    path = log.path_for("alice")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("complete\npartial-no-newline")  # only `complete` is a finished line
    lines, offset = log.read_from("alice", offset=0)
    assert lines == ["complete"]
    assert offset == len("complete\n")


def test_cursor_store_round_trip(tmp_path: Path) -> None:
    store = CursorStore(tmp_path)
    assert store.get("alice") == 0
    store.set("alice", 42)
    assert store.get("alice") == 42
    # New instance re-reads from disk
    store2 = CursorStore(tmp_path)
    assert store2.get("alice") == 42


def test_outbox_append(tmp_path: Path) -> None:
    log = OutboxLog(tmp_path)
    log.append("alice", "first sent")
    log.append("alice", "second sent")
    assert log.path_for("alice").read_text() == "first sent\nsecond sent\n"


def test_outbox_read_all(tmp_path: Path) -> None:
    log = OutboxLog(tmp_path)
    log.append("alice", "a")
    log.append("alice", "b")
    assert log.read_all("alice") == ["a", "b"]
    assert log.read_all("nobody") == []


def test_registry_records_first_and_last_seen(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("alice", now="2026-04-22T00:00:00Z", wrote=False)
    reg.touch("alice", now="2026-04-22T00:05:00Z", wrote=True)
    entry = reg.get("alice")
    assert entry["firstSeenAt"] == "2026-04-22T00:00:00Z"
    assert entry["lastSeenAt"] == "2026-04-22T00:05:00Z"
    assert entry["lastWriteAt"] == "2026-04-22T00:05:00Z"


def test_registry_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "identities.json"
    reg = IdentityRegistry(path)
    reg.touch("alice", now="2026-04-22T00:00:00Z", wrote=True)
    reg2 = IdentityRegistry(path)
    assert reg2.get("alice")["firstSeenAt"] == "2026-04-22T00:00:00Z"


def test_registry_list_all(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("alice", now="t1", wrote=False)
    reg.touch("bob", now="t1", wrote=False)
    assert sorted(reg.all()) == ["alice", "bob"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_storage.py -v`
Expected: all fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `broker_storage.py`**

```python
#!/usr/bin/env python3
"""On-disk primitives for the DM broker.

    ~/.mcp-broker/
      inbox/<encoded-identity>.log     # newline-delimited display-format lines, per-identity
      outbox/<encoded-identity>.log    # same, but for messages this identity sent
      cursors/<encoded-identity>.cursor  # byte offset into inbox log for read-cursor
      identities.json                  # registry of known identities
"""

import json
from pathlib import Path


def encode_identity(identity: str) -> str:
    """Filesystem-safe form of an identity. Replaces `/` with `_`.

    Package names and `<org>/<repo>` are the only expected forms, and `/` is
    the only path-unsafe character they use. Case is preserved; the registry
    handles case-insensitive lookup.
    """
    return identity.replace("/", "_")


class InboxLog:
    """Append-only log of messages delivered to an identity."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def path_for(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.log"

    def append(self, identity: str, line: str) -> None:
        """Append `line` (no trailing newline) to the identity's inbox. Adds newline."""
        path = self.path_for(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")

    def read_from(self, identity: str, offset: int) -> tuple[list[str], int]:
        """Return (complete lines after `offset`, new byte offset after the last complete line).

        A trailing partial line (no newline terminator) is NOT returned and does
        NOT advance the offset — it'll be picked up once the writer finishes the line.
        """
        path = self.path_for(identity)
        if not path.exists():
            return [], offset
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
        if not data:
            return [], offset
        # Keep only complete (newline-terminated) lines.
        last_nl = data.rfind(b"\n")
        if last_nl < 0:
            return [], offset
        complete = data[: last_nl + 1]
        lines = complete.decode().splitlines()
        return lines, offset + len(complete)


class OutboxLog:
    """Append-only log of messages sent by an identity."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def path_for(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.log"

    def append(self, identity: str, line: str) -> None:
        path = self.path_for(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")

    def read_all(self, identity: str) -> list[str]:
        path = self.path_for(identity)
        if not path.exists():
            return []
        return path.read_text().splitlines()


class CursorStore:
    """Per-identity byte offset into the inbox log."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def _path(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.cursor"

    def get(self, identity: str) -> int:
        path = self._path(identity)
        if not path.exists():
            return 0
        try:
            return int(path.read_text().strip())
        except ValueError:
            return 0

    def set(self, identity: str, offset: int) -> None:
        path = self._path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".cursor.tmp")
        tmp.write_text(str(offset))
        tmp.replace(path)


class IdentityRegistry:
    """Durable record of which identities have connected. Case-insensitive lookup."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._entries = json.loads(self.path.read_text())

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._entries, indent=2, sort_keys=True))
        tmp.replace(self.path)

    def _key(self, identity: str) -> str:
        return identity.lower()

    def touch(self, identity: str, now: str, wrote: bool) -> None:
        """Record a connection event. `wrote=True` also updates lastWriteAt."""
        key = self._key(identity)
        entry = self._entries.get(key, {})
        if "firstSeenAt" not in entry:
            entry["firstSeenAt"] = now
            entry["canonical"] = identity
        entry["lastSeenAt"] = now
        if wrote:
            entry["lastWriteAt"] = now
        self._entries[key] = entry
        self._save()

    def get(self, identity: str) -> dict | None:
        return self._entries.get(self._key(identity))

    def all(self) -> list[str]:
        return [e.get("canonical", k) for k, e in self._entries.items()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_storage.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_storage.py tests/test_broker_storage.py
git commit -m "feat(broker): inbox/outbox logs, cursor store, identity registry"
```

---

## Phase 2: Server DM handlers

### Task 5: Wire DM storage into `BrokerServer`

**Files:**
- Modify: `scripts/broker_server.py` (constructor + new attributes)
- Test: `tests/test_broker_dm_server.py` (new)

- [ ] **Step 1: Write a smoke test for storage wiring**

```python
# tests/test_broker_dm_server.py
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer


def test_server_initializes_dm_storage(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    # The inbox, outbox, cursors subdirectories are siblings of conversations/
    assert server.inbox_log.base_dir == tmp_path / "inbox"
    assert server.outbox_log.base_dir == tmp_path / "outbox"
    assert server.cursors.base_dir == tmp_path / "cursors"
    assert server.registry.path == tmp_path / "identities.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: FAIL with `AttributeError: 'BrokerServer' object has no attribute 'inbox_log'`.

- [ ] **Step 3: Modify `BrokerServer.__init__` to wire DM storage**

At the top of `scripts/broker_server.py`, add imports:

```python
from broker_storage import InboxLog, OutboxLog, CursorStore, IdentityRegistry
```

Replace the existing `__init__` with:

```python
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir  # conversations dir (legacy rooms)
        self.conversations: dict[str, dict] = {}
        self.members: dict[str, set[str]] = {}
        self.clients: dict[str, Callable] = {}
        # DM model: inbox/outbox/cursors live as siblings of conversations/.
        root = storage_dir.parent
        self.inbox_log = InboxLog(root / "inbox")
        self.outbox_log = OutboxLog(root / "outbox")
        self.cursors = CursorStore(root / "cursors")
        self.registry = IdentityRegistry(root / "identities.json")
        self._load_from_disk()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: 1 passed.

- [ ] **Step 5: Run the full suite to make sure nothing regressed**

Run: `python -m pytest tests/ -v`
Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): wire inbox/outbox/cursors/registry into BrokerServer"
```

---

### Task 6: `send_dm` handler (single + multi recipient)

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_broker_dm_server.py`:

```python
def _send(server: BrokerServer, identity: str, **kwargs) -> dict:
    """Helper that invokes handle_request and unwraps the data/error."""
    result = server.handle_request(identity, {"type": "send_dm", "id": "req-x", **kwargs})
    if result["type"] == "error":
        raise ValueError(result["message"])
    return result["data"]


def test_send_dm_delivers_to_single_recipient(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    data = _send(server, "alice", to=["bob"], content="hello bob")
    assert "message_id" in data
    lines, _ = server.inbox_log.read_from("bob", 0)
    assert len(lines) == 1
    assert "[alice]" in lines[0]
    assert lines[0].endswith("hello bob")


def test_send_dm_delivers_to_multiple_recipients(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob", "carol"], content="group ping")
    bob_lines, _ = server.inbox_log.read_from("bob", 0)
    carol_lines, _ = server.inbox_log.read_from("carol", 0)
    assert len(bob_lines) == 1 and len(carol_lines) == 1
    assert "bob" in bob_lines[0] or " → " in bob_lines[0]  # multi-recipient arrow present


def test_send_dm_writes_sender_outbox(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob"], content="audit me")
    sent = server.outbox_log.read_all("alice")
    assert len(sent) == 1
    assert "audit me" in sent[0]


def test_send_dm_rejects_broadcast_sentinel(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    with pytest.raises(ValueError, match="BROADCAST"):
        _send(server, "alice", to=["BROADCAST"], content="nope")


def test_send_dm_pushes_to_connected_recipient(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    received: list[dict] = []
    server.connect("alice", lambda m: None)
    server.connect("bob", received.append)
    _send(server, "alice", to=["bob"], content="live push")
    assert any(m.get("type") == "inbox_message" for m in received)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all new tests FAIL with `Unknown request type: send_dm`.

- [ ] **Step 3: Implement `_handle_send_dm` and register it**

In `scripts/broker_server.py`, add the following imports:

```python
from broker_constants import BROADCAST
from broker_format import format_message
```

Register the handler in the dispatch dict inside `handle_request`:

```python
            handler = {
                "create_conversation": self._handle_create,
                "join_conversation": self._handle_join,
                "leave_conversation": self._handle_leave,
                "send_message": self._handle_send,
                "history": self._handle_history,
                "list_conversations": self._handle_list,
                "list_members": self._handle_list_members,
                "close_conversation": self._handle_close,
                "send_dm": self._handle_send_dm,
            }.get(msg_type)
```

Add the handler method:

```python
    def _handle_send_dm(self, identity: str, msg: dict) -> dict:
        """Handle a direct-message send.

        msg: { type, id, to: [identity, ...], content }
        Rejects if `to` contains BROADCAST (use send_broadcast instead).
        Appends to each recipient's inbox log, appends to sender's outbox log,
        and pushes `inbox_message` to each online recipient.
        """
        to = msg.get("to") or []
        content = msg.get("content", "")
        if BROADCAST in to:
            raise ValueError("BROADCAST is not a valid recipient; use send_broadcast.")
        if not to:
            raise ValueError("send_dm requires at least one recipient in `to`.")

        message_id = self._message_id()
        timestamp = self._timestamp()
        # Persist the underlying record for reply-all lookup.
        self._record_dm(message_id, identity, to, timestamp, content, is_broadcast=False)

        # Per-recipient rendering (each sees `you` for themselves).
        for recipient in to:
            line = format_message(timestamp, identity, to, content, viewer=recipient)
            self.inbox_log.append(recipient, line)
            if recipient in self.clients and recipient != identity:
                self.clients[recipient]({
                    "type": "inbox_message",
                    "message_id": message_id,
                    "recipient": recipient,
                    "line": line,
                })

        # Sender's outbox: render from the sender's perspective.
        sender_line = format_message(timestamp, identity, to, content, viewer=identity)
        self.outbox_log.append(identity, sender_line)

        self.registry.touch(identity, now=timestamp, wrote=True)
        return {"message_id": message_id, "recipients": list(to)}
```

Add a helper that persists DM records so reply-all can later look them up. Place it near the other helpers:

```python
    def _record_dm(
        self,
        message_id: str,
        sender: str,
        to: list[str],
        timestamp: str,
        content: str,
        is_broadcast: bool,
    ) -> None:
        """Store the raw fields needed to answer reply-all queries."""
        self.storage_dir.parent.joinpath("messages").mkdir(parents=True, exist_ok=True)
        record = {
            "id": message_id,
            "sender": sender,
            "to": list(to),
            "timestamp": timestamp,
            "content": content,
            "is_broadcast": is_broadcast,
        }
        path = self.storage_dir.parent / "messages" / f"{message_id}.json"
        path.write_text(json.dumps(record))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all 5 new tests pass; existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): send_dm handler — per-recipient inbox + sender outbox"
```

---

### Task 7: `broadcast` handler

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Add failing tests**

```python
def _broadcast(server: BrokerServer, identity: str, content: str) -> dict:
    result = server.handle_request(identity, {"type": "send_broadcast", "id": "x", "content": content})
    if result["type"] == "error":
        raise ValueError(result["message"])
    return result["data"]


def test_broadcast_delivers_to_every_registered_identity(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    server.connect("carol", lambda m: None)
    # Register all three by having each send a DM.
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "seed"})
    server.handle_request("bob", {"type": "send_dm", "id": "2", "to": ["carol"], "content": "seed"})
    server.handle_request("carol", {"type": "send_dm", "id": "3", "to": ["alice"], "content": "seed"})

    _broadcast(server, "alice", "announcement")
    for recipient in ("alice", "bob", "carol"):
        lines, _ = server.inbox_log.read_from(recipient, 0)
        assert any("→ BROADCAST" in line and line.endswith("announcement") for line in lines)


def test_broadcast_writes_sender_outbox(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["alice"], "content": "self"})
    _broadcast(server, "alice", "hello world")
    sent = server.outbox_log.read_all("alice")
    assert any("→ BROADCAST" in line for line in sent)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_server.py::test_broadcast_delivers_to_every_registered_identity -v`
Expected: FAIL with `Unknown request type: send_broadcast`.

- [ ] **Step 3: Implement `_handle_broadcast`**

Register `"send_broadcast": self._handle_broadcast` in the dispatch dict.

Add the method:

```python
    def _handle_broadcast(self, identity: str, msg: dict) -> dict:
        """Fan out to every registered identity's inbox."""
        content = msg.get("content", "")
        message_id = self._message_id()
        timestamp = self._timestamp()
        recipients = [BROADCAST]
        self._record_dm(message_id, identity, recipients, timestamp, content, is_broadcast=True)

        for dest in self.registry.all():
            line = format_message(timestamp, identity, recipients, content, viewer=dest)
            self.inbox_log.append(dest, line)
            if dest in self.clients and dest != identity:
                self.clients[dest]({
                    "type": "inbox_message",
                    "message_id": message_id,
                    "recipient": dest,
                    "line": line,
                })

        sender_line = format_message(timestamp, identity, recipients, content, viewer=identity)
        self.outbox_log.append(identity, sender_line)
        self.registry.touch(identity, now=timestamp, wrote=True)
        return {"message_id": message_id, "recipient_count": len(self.registry.all())}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): send_broadcast fans out to all registered identities"
```

---

### Task 8: `reply_all` handler

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Add failing tests**

```python
def test_reply_all_computes_recipient_set(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    server.connect("carol", lambda m: None)
    sent = server.handle_request("alice", {
        "type": "send_dm", "id": "1", "to": ["bob", "carol"], "content": "kickoff",
    })["data"]
    orig_id = sent["message_id"]

    result = server.handle_request("bob", {
        "type": "reply_all", "id": "2", "to_message": orig_id, "content": "replying",
    })
    assert result["type"] == "response"
    # Reply-all from bob should go to [alice, carol] (original sender + others − bob)
    assert set(result["data"]["recipients"]) == {"alice", "carol"}

    alice_lines, _ = server.inbox_log.read_from("alice", 0)
    carol_lines, _ = server.inbox_log.read_from("carol", 0)
    bob_lines, _ = server.inbox_log.read_from("bob", 0)
    assert any(line.endswith("replying") for line in alice_lines)
    assert any(line.endswith("replying") for line in carol_lines)
    assert not any(line.endswith("replying") for line in bob_lines)  # no self-echo


def test_reply_all_rejects_broadcast_message(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "seed", "to": ["alice"], "content": "s"})
    bcast = server.handle_request("alice", {"type": "send_broadcast", "id": "1", "content": "hi all"})
    result = server.handle_request("alice", {
        "type": "reply_all", "id": "2", "to_message": bcast["data"]["message_id"], "content": "nope",
    })
    assert result["type"] == "error"
    assert "broadcast" in result["message"].lower()


def test_reply_all_unknown_message_errors(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "type": "reply_all", "id": "2", "to_message": "msg-does-not-exist", "content": "x",
    })
    assert result["type"] == "error"
    assert "not found" in result["message"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_server.py -k reply_all -v`
Expected: FAIL with `Unknown request type: reply_all`.

- [ ] **Step 3: Implement `_handle_reply_all`**

Register `"reply_all": self._handle_reply_all` in the dispatch dict.

Add the helper and handler:

```python
    def _load_message_record(self, message_id: str) -> dict | None:
        path = self.storage_dir.parent / "messages" / f"{message_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _handle_reply_all(self, identity: str, msg: dict) -> dict:
        """Reply to everyone on a prior DM thread (excluding self).

        Rejects if the target message was a broadcast.
        """
        record = self._load_message_record(msg["to_message"])
        if record is None:
            raise ValueError(f"Message '{msg['to_message']}' not found")
        if record["is_broadcast"]:
            raise ValueError("Cannot reply-all to a broadcast; use send_dm instead.")

        recipients = [record["sender"]] + list(record["to"])
        recipients = [r for r in recipients if r != identity]
        # Dedup preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for r in recipients:
            if r not in seen:
                seen.add(r)
                ordered.append(r)
        if not ordered:
            raise ValueError("reply-all yielded an empty recipient set (you were the only party).")

        return self._handle_send_dm(identity, {
            "type": "send_dm",
            "id": msg.get("id", ""),
            "to": ordered,
            "content": msg.get("content", ""),
        })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): reply_all computes recipient set from original message"
```

---

### Task 9: `history_inbox` and `read_inbox` handlers

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Add failing tests**

```python
def test_history_inbox_returns_all_without_advancing_cursor(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "first"})
    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "second"})

    before_cursor = server.cursors.get("bob")
    result = server.handle_request("bob", {"type": "history_inbox", "id": "x"})
    assert result["type"] == "response"
    lines = result["data"]["lines"]
    assert len(lines) == 2
    assert server.cursors.get("bob") == before_cursor  # cursor unchanged


def test_history_inbox_filters_by_sender(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.connect("carol", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "from alice"})
    server.handle_request("carol", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "from carol"})

    result = server.handle_request("bob", {"type": "history_inbox", "id": "x", "from": "alice"})
    lines = result["data"]["lines"]
    assert len(lines) == 1
    assert "from alice" in lines[0]


def test_history_sent_reads_outbox(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "sent 1"})
    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["carol"], "content": "sent 2"})

    result = server.handle_request("alice", {"type": "history_inbox", "id": "x", "sent": True})
    lines = result["data"]["lines"]
    assert len(lines) == 2
    assert any("sent 1" in line for line in lines)
    assert any("sent 2" in line for line in lines)


def test_read_inbox_advances_cursor_and_returns_only_new(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "one"})

    first = server.handle_request("bob", {"type": "read_inbox", "id": "x"})
    assert len(first["data"]["lines"]) == 1

    second = server.handle_request("bob", {"type": "read_inbox", "id": "y"})
    assert second["data"]["lines"] == []

    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "two"})
    third = server.handle_request("bob", {"type": "read_inbox", "id": "z"})
    assert len(third["data"]["lines"]) == 1
    assert third["data"]["lines"][0].endswith("two")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_server.py -k "history_inbox or read_inbox" -v`
Expected: FAIL with `Unknown request type`.

- [ ] **Step 3: Implement handlers**

Register in the dispatch dict:

```python
                "history_inbox": self._handle_history_inbox,
                "read_inbox": self._handle_read_inbox,
```

Add the methods:

```python
    def _handle_history_inbox(self, identity: str, msg: dict) -> dict:
        """Read the identity's inbox (or outbox, with `sent=True`) without advancing the cursor.

        Optional filters:
            from: only lines whose sender matches this identity
            since: only lines with timestamp >= this ISO8601 string
            with_ids: include the underlying message IDs in the returned records
        """
        sent = bool(msg.get("sent"))
        if sent:
            lines = self.outbox_log.read_all(identity)
        else:
            lines, _ = self.inbox_log.read_from(identity, 0)

        from_filter = msg.get("from")
        since = msg.get("since")
        if from_filter or since:
            from broker_format import parse_message
            filtered: list[str] = []
            for line in lines:
                try:
                    parsed = parse_message(line, viewer=identity)
                except ValueError:
                    continue
                if from_filter and parsed.sender != from_filter:
                    continue
                if since and parsed.timestamp < since:
                    continue
                filtered.append(line)
            lines = filtered
        self.registry.touch(identity, now=self._timestamp(), wrote=False)
        return {"lines": lines}

    def _handle_read_inbox(self, identity: str, msg: dict) -> dict:
        """Return inbox lines since the identity's last read-cursor; advance the cursor."""
        offset = self.cursors.get(identity)
        lines, new_offset = self.inbox_log.read_from(identity, offset)
        self.cursors.set(identity, new_offset)
        self.registry.touch(identity, now=self._timestamp(), wrote=False)
        return {"lines": lines}
```

Move the `from broker_format import parse_message` up to the top of the file to avoid repeated imports (the inline `from` inside the method is kept above only to minimize the diff).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): history_inbox (cursor-free) and read_inbox (cursor-advancing)"
```

---

### Task 10: Reserved-identity enforcement

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Add failing tests**

```python
def test_reserved_identity_requires_token(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("bob", lambda m: None)
    with pytest.raises(ValueError, match="reserved"):
        server.handle_request("orchestrator", {
            "type": "send_dm", "id": "1", "to": ["bob"], "content": "i'm not the real orch",
        })


def test_reserved_identity_with_token_allowed(tmp_path: Path) -> None:
    root = tmp_path
    token_dir = root / "tokens"
    token_dir.mkdir()
    (token_dir / "orchestrator.token").write_text("ok")

    server = BrokerServer(storage_dir=root / "conversations")
    server.connect("orchestrator", lambda m: None, token="ok")
    server.connect("bob", lambda m: None)
    server.handle_request("orchestrator", {
        "type": "send_dm", "id": "1", "to": ["bob"], "content": "orchestrator here",
    })
    lines, _ = server.inbox_log.read_from("bob", 0)
    assert any("[orchestrator]" in line for line in lines)


def test_broadcast_identity_cannot_be_claimed(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    with pytest.raises(ValueError, match="reserved"):
        server.connect("BROADCAST", lambda m: None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_server.py -k reserved -v`
Expected: FAIL (the server currently accepts anything).

- [ ] **Step 3: Implement enforcement**

Update `BrokerServer.connect` signature and logic:

```python
    def connect(self, identity: str, send: Callable, token: str | None = None) -> None:
        """Register a client connection. Reserved identities require a matching token."""
        from broker_constants import RESERVED_IDENTITIES
        if identity in RESERVED_IDENTITIES:
            if identity == "BROADCAST":
                raise ValueError("BROADCAST is reserved and cannot be claimed as an identity.")
            expected = self._read_token(identity)
            if expected is None or token != expected:
                raise ValueError(f"Identity '{identity}' is reserved; a valid token is required.")
        self.clients[identity] = send
        self.registry.touch(identity, now=self._timestamp(), wrote=False)

    def _read_token(self, identity: str) -> str | None:
        """Read the contents of ~/.mcp-broker/tokens/<identity>.token, or None."""
        path = self.storage_dir.parent / "tokens" / f"{identity}.token"
        if not path.exists():
            return None
        return path.read_text().strip()
```

Also update `handle_request` to reject if a reserved identity is used without a prior privileged `connect`:

```python
    def handle_request(self, identity: str, msg: dict) -> dict:
        req_id = msg.get("id", "")
        msg_type = msg.get("type", "")
        # Reserved identities cannot be used in handle_request unless they were
        # connected via a privileged path (connect() validates the token).
        from broker_constants import RESERVED_IDENTITIES
        if identity in RESERVED_IDENTITIES and identity not in self.clients:
            return {
                "type": "error",
                "id": req_id,
                "message": f"Identity '{identity}' is reserved; connect with a valid token first.",
            }
        # ... rest unchanged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_server.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): enforce reserved identities via per-host token files"
```

---

## Phase 3: Client + CLI

### Task 11: `BrokerClient` DM methods

**Files:**
- Modify: `scripts/broker_client.py`
- Test: `tests/test_broker_client.py` (extend)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_broker_client.py`:

```python
@pytest.mark.asyncio
async def test_send_dm_round_trip(tmp_path: Path):
    sock = str(tmp_path / "broker.sock")
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    srv = await start_server(server, sock)

    alice = BrokerClient("alice", sock); await alice.connect()
    bob = BrokerClient("bob", sock); await bob.connect()
    try:
        result = await alice.send_dm(["bob"], "hello bob")
        assert "message_id" in result
    finally:
        await alice.close()
        await bob.close()
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_broadcast_round_trip(tmp_path: Path):
    sock = str(tmp_path / "broker.sock")
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    srv = await start_server(server, sock)

    alice = BrokerClient("alice", sock); await alice.connect()
    bob = BrokerClient("bob", sock); await bob.connect()
    try:
        await alice.send_dm(["bob"], "seed")  # registers alice + bob
        result = await alice.broadcast("to all")
        assert result["recipient_count"] >= 2
    finally:
        await alice.close(); await bob.close()
        srv.close(); await srv.wait_closed()


@pytest.mark.asyncio
async def test_reply_all_round_trip(tmp_path: Path):
    sock = str(tmp_path / "broker.sock")
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    srv = await start_server(server, sock)

    alice = BrokerClient("alice", sock); await alice.connect()
    bob = BrokerClient("bob", sock); await bob.connect()
    carol = BrokerClient("carol", sock); await carol.connect()
    try:
        sent = await alice.send_dm(["bob", "carol"], "kickoff")
        reply = await bob.reply_all(sent["message_id"], "responding")
        assert set(reply["recipients"]) == {"alice", "carol"}
    finally:
        for c in (alice, bob, carol): await c.close()
        srv.close(); await srv.wait_closed()


@pytest.mark.asyncio
async def test_history_inbox_and_read_inbox(tmp_path: Path):
    sock = str(tmp_path / "broker.sock")
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    srv = await start_server(server, sock)

    alice = BrokerClient("alice", sock); await alice.connect()
    bob = BrokerClient("bob", sock); await bob.connect()
    try:
        await alice.send_dm(["bob"], "one")
        await alice.send_dm(["bob"], "two")
        hist = await bob.history_inbox()
        assert len(hist["lines"]) == 2
        first = await bob.read_inbox()
        assert len(first["lines"]) == 2
        second = await bob.read_inbox()
        assert second["lines"] == []
    finally:
        await alice.close(); await bob.close()
        srv.close(); await srv.wait_closed()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_client.py -v`
Expected: new tests FAIL with `AttributeError: 'BrokerClient' object has no attribute 'send_dm'`.

- [ ] **Step 3: Implement the new methods on `BrokerClient`**

Append to `scripts/broker_client.py`:

```python
    async def send_dm(self, to: list[str], content: str) -> dict:
        """Send a direct message to one or more recipients."""
        return await self._request({"type": "send_dm", "to": to, "content": content})

    async def broadcast(self, content: str) -> dict:
        """Broadcast to every registered identity."""
        return await self._request({"type": "send_broadcast", "content": content})

    async def reply_all(self, to_message: str, content: str) -> dict:
        """Reply to everyone on a prior DM (excluding self)."""
        return await self._request({
            "type": "reply_all", "to_message": to_message, "content": content,
        })

    async def history_inbox(
        self, *, sender: str | None = None, since: str | None = None, sent: bool = False,
    ) -> dict:
        """Read inbox (or outbox with `sent=True`) without advancing the cursor."""
        msg: dict = {"type": "history_inbox"}
        if sender: msg["from"] = sender
        if since: msg["since"] = since
        if sent: msg["sent"] = True
        return await self._request(msg)

    async def read_inbox(self) -> dict:
        """Read new inbox lines since the last read-cursor; advances the cursor."""
        return await self._request({"type": "read_inbox"})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_client.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_client.py tests/test_broker_client.py
git commit -m "feat(broker): client methods for send_dm, broadcast, reply_all, history, read"
```

---

### Task 12: CLI — `broker send --to`

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_broker_dm_cli.py
import asyncio
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CLI = [sys.executable, str(SCRIPTS / "broker_cli.py")]


@pytest.fixture
def broker(tmp_path: Path):
    """Start a broker server against tmp_path and yield a dict of paths + env."""
    sock = tmp_path / "broker.sock"
    storage = tmp_path / "conversations"
    env = {"MCP_BROKER_SOCK": str(sock), "MCP_BROKER_STORAGE": str(storage)}
    # Start server in the background.
    proc = subprocess.Popen(
        CLI + ["server"],
        env={**env, "PATH": Path(sys.executable).parent.as_posix()},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Wait for socket to appear (max 3s).
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        proc.terminate()
        raise RuntimeError("broker server did not start")
    yield {"env": env, "tmp": tmp_path}
    proc.terminate()
    proc.wait(timeout=3)


def test_send_dm_writes_to_recipient_inbox(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "hello bob"],
        env={**env, "PATH": Path(sys.executable).parent.as_posix()},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    inbox_line = (broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "[alice]" in inbox_line
    assert inbox_line.strip().endswith("hello bob")


def test_send_dm_multi_recipient(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "group ping"],
        env={**env, "PATH": Path(sys.executable).parent.as_posix()},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (broker["tmp"] / "inbox" / "bob.log").exists()
    assert (broker["tmp"] / "inbox" / "carol.log").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_send_dm_writes_to_recipient_inbox -v`
Expected: FAIL — either `send` is unknown to the CLI, or `MCP_BROKER_STORAGE` is not honored.

- [ ] **Step 3: Implement the `send` subcommand in `broker_cli.py`**

At the top of `broker_cli.py`, add env-override support for the storage dir (so tests can point it at `tmp_path`). Find `main()`'s socket-resolution logic and mirror it for storage. Then add a new subparser:

```python
def _add_dm_subparsers(subparsers) -> None:
    send = subparsers.add_parser("send", help="Send a DM to one or more identities")
    send.add_argument("--identity", required=False, help="Sender identity (defaults to cwd-derived)")
    send.add_argument("--to", required=True, help="Comma-separated recipient identities")
    send.add_argument("content", help="Message body")
    send.set_defaults(func=_cmd_send)


def _cmd_send(args, sock_path: str) -> int:
    from broker_identity import derive_identity, IdentityDerivationError
    identity = args.identity
    if identity is None:
        try:
            identity = derive_identity(Path.cwd())
        except IdentityDerivationError as e:
            print(f"error: {e}", file=sys.stderr); return 1

    async def run() -> int:
        client = BrokerClient(identity, sock_path)
        await client.connect()
        try:
            result = await client.send_dm([r.strip() for r in args.to.split(",")], args.content)
            print(result["message_id"])
            return 0
        finally:
            await client.close()

    return asyncio.run(run())
```

In the main arg-parsing block, call `_add_dm_subparsers(subparsers)` and ensure dispatch uses `args.func` when present.

Also modify `BrokerServer.__init__` (already done in Task 5) to respect a new `MCP_BROKER_STORAGE` env var at the CLI's `server` subcommand entry point, so tests can redirect storage:

```python
def _run_server(args) -> int:
    sock_path = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
    storage = Path(os.environ.get("MCP_BROKER_STORAGE", str(Path.home() / ".mcp-broker" / "conversations")))
    server = BrokerServer(storage_dir=storage)
    asyncio.run(_serve_forever(server, sock_path))
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_cli.py -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'send --to' subcommand, env-configurable storage"
```

---

### Task 13: CLI — `broker broadcast`

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_broadcast_fans_out(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    # Register alice and bob by each sending a DM to the other.
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "seed"], **envargs)
    subprocess.run(CLI + ["send", "--identity", "bob", "--to", "alice", "seed"], **envargs)
    # Broadcast from alice.
    result = subprocess.run(CLI + ["broadcast", "--identity", "alice", "announcement"], **envargs)
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    bob_inbox = (broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "→ BROADCAST" in alice_inbox
    assert "→ BROADCAST" in bob_inbox
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_broadcast_fans_out -v`
Expected: FAIL with unknown subcommand.

- [ ] **Step 3: Add the `broadcast` subcommand**

In `_add_dm_subparsers`:

```python
    bcast = subparsers.add_parser("broadcast", help="Send a broadcast to every registered identity")
    bcast.add_argument("--identity", required=False)
    bcast.add_argument("content")
    bcast.set_defaults(func=_cmd_broadcast)


def _cmd_broadcast(args, sock_path: str) -> int:
    from broker_identity import derive_identity, IdentityDerivationError
    identity = args.identity or derive_identity(Path.cwd())

    async def run() -> int:
        client = BrokerClient(identity, sock_path)
        await client.connect()
        try:
            result = await client.broadcast(args.content)
            print(result["message_id"])
            return 0
        finally:
            await client.close()

    return asyncio.run(run())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_broadcast_fans_out -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'broadcast' subcommand"
```

---

### Task 14: CLI — `broker reply-all`

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_reply_all_cli(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    sent = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "kickoff"], **envargs,
    )
    message_id = sent.stdout.strip()
    assert sent.returncode == 0 and message_id.startswith("msg-")

    result = subprocess.run(
        CLI + ["reply-all", "--identity", "bob", "--to-message", message_id, "responding"],
        **envargs,
    )
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    carol_inbox = (broker["tmp"] / "inbox" / "carol.log").read_text()
    bob_inbox_path = broker["tmp"] / "inbox" / "bob.log"
    bob_inbox = bob_inbox_path.read_text() if bob_inbox_path.exists() else ""
    assert "responding" in alice_inbox
    assert "responding" in carol_inbox
    assert "responding" not in bob_inbox  # no self-echo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_reply_all_cli -v`
Expected: FAIL with unknown subcommand.

- [ ] **Step 3: Add the `reply-all` subcommand**

In `_add_dm_subparsers`:

```python
    ra = subparsers.add_parser("reply-all", help="Reply to all recipients of a prior DM")
    ra.add_argument("--identity", required=False)
    ra.add_argument("--to-message", required=True)
    ra.add_argument("content")
    ra.set_defaults(func=_cmd_reply_all)


def _cmd_reply_all(args, sock_path: str) -> int:
    from broker_identity import derive_identity
    identity = args.identity or derive_identity(Path.cwd())

    async def run() -> int:
        client = BrokerClient(identity, sock_path)
        await client.connect()
        try:
            result = await client.reply_all(args.to_message, args.content)
            print(result["message_id"])
            return 0
        finally:
            await client.close()

    return asyncio.run(run())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_reply_all_cli -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'reply-all' subcommand"
```

---

### Task 15: CLI — `broker history`

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_history_cli(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "one"], **envargs)
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "two"], **envargs)
    result = subprocess.run(CLI + ["history", "--identity", "bob"], **envargs)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("one")
    assert lines[1].endswith("two")


def test_history_cli_sent_flag(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "sent one"], **envargs)
    result = subprocess.run(CLI + ["history", "--identity", "alice", "--sent"], **envargs)
    assert result.returncode == 0
    assert "sent one" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py -k history -v`
Expected: FAIL with unknown subcommand.

- [ ] **Step 3: Add the `history` subcommand**

In `_add_dm_subparsers`:

```python
    hist = subparsers.add_parser("history", help="Read inbox (or outbox) without advancing the cursor")
    hist.add_argument("--identity", required=False)
    hist.add_argument("--from", dest="from_filter", help="Only lines from this sender")
    hist.add_argument("--since", help="Only lines with timestamp >= this ISO8601 string")
    hist.add_argument("--sent", action="store_true", help="Read the sender's outbox instead of inbox")
    hist.set_defaults(func=_cmd_history)


def _cmd_history(args, sock_path: str) -> int:
    from broker_identity import derive_identity
    identity = args.identity or derive_identity(Path.cwd())

    async def run() -> int:
        client = BrokerClient(identity, sock_path)
        await client.connect()
        try:
            result = await client.history_inbox(
                sender=args.from_filter, since=args.since, sent=args.sent,
            )
            for line in result["lines"]:
                print(line)
            return 0
        finally:
            await client.close()

    return asyncio.run(run())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_cli.py -k history -v`
Expected: both pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'history' subcommand — inbox/outbox, no cursor advance"
```

---

### Task 16: CLI — `broker read` (inbox mode)

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

The existing `broker read` takes a conversation ID; the new DM form takes none. Detect the shape: if no positional argument is provided, use inbox mode; otherwise preserve the legacy path.

- [ ] **Step 1: Add failing test**

```python
def test_read_cli_inbox_mode(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "msg1"], **envargs)
    first = subprocess.run(CLI + ["read", "--identity", "bob"], **envargs)
    assert first.returncode == 0
    assert "msg1" in first.stdout
    second = subprocess.run(CLI + ["read", "--identity", "bob"], **envargs)
    assert second.stdout.strip() == ""  # cursor moved past
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_read_cli_inbox_mode -v`
Expected: FAIL (existing `read` requires a conversation ID).

- [ ] **Step 3: Modify the `read` subparser to make `conversation_id` optional**

Locate the existing `read` subparser. Change its positional `conversation_id` to optional (`nargs='?'`), and update the dispatch:

```python
def _cmd_read(args, sock_path: str) -> int:
    if args.conversation_id is None:
        # DM inbox mode
        from broker_identity import derive_identity
        identity = args.identity or derive_identity(Path.cwd())

        async def run_inbox() -> int:
            client = BrokerClient(identity, sock_path)
            await client.connect()
            try:
                result = await client.read_inbox()
                for line in result["lines"]:
                    print(line)
                return 0
            finally:
                await client.close()

        return asyncio.run(run_inbox())
    # Legacy room read path — unchanged.
    return _cmd_read_legacy(args, sock_path)
```

Rename the existing body of the read handler to `_cmd_read_legacy`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ -v`
Expected: new test passes; all legacy tests still pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'read' without conv-id reads DM inbox and advances cursor"
```

---

### Task 17: CLI — `broker follow` tails inbox file

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_follow_tails_inbox_file(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}}

    # Pre-populate one message so follow has something to drain.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "backlog msg"],
        capture_output=True, text=True, **envargs,
    )

    # Start follow in background. It should print the backlog line, then block.
    follow = subprocess.Popen(
        CLI + ["follow", "--identity", "bob", "--idle-timeout", "2"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **envargs,
    )
    time.sleep(0.3)
    # Send a live message while follow is running.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "live msg"],
        capture_output=True, text=True, **envargs,
    )
    stdout, stderr = follow.communicate(timeout=5)
    assert "backlog msg" in stdout, stderr
    assert "live msg" in stdout, stderr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_follow_tails_inbox_file -v`
Expected: FAIL (either unknown subcommand, or the existing `follow` requires a conversation ID).

- [ ] **Step 3: Implement inbox-tail `follow`**

Locate the existing `follow` subparser. Change its positional `conversation_id` to optional. Then add an inbox-tail code path:

```python
def _cmd_follow(args, sock_path: str) -> int:
    if args.conversation_id is not None:
        return _cmd_follow_legacy(args, sock_path)

    from broker_identity import derive_identity
    identity = args.identity or derive_identity(Path.cwd())
    storage_root = Path(os.environ.get("MCP_BROKER_STORAGE", str(Path.home() / ".mcp-broker" / "conversations"))).parent
    from broker_storage import InboxLog, CursorStore
    inbox = InboxLog(storage_root / "inbox")
    cursors = CursorStore(storage_root / "cursors")

    # Drain from cursor, then block reading new lines via polling.
    idle_timeout = float(args.idle_timeout or 300)
    poll_interval = 0.2
    last_activity = time.monotonic()

    while True:
        offset = cursors.get(identity)
        lines, new_offset = inbox.read_from(identity, offset)
        if lines:
            for line in lines:
                print(line, flush=True)
            cursors.set(identity, new_offset)
            last_activity = time.monotonic()
        if time.monotonic() - last_activity >= idle_timeout:
            return 0
        time.sleep(poll_interval)
```

Rename the existing body to `_cmd_follow_legacy`.

Add `import os` and `import time` to the top of the file if not already present.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_follow_tails_inbox_file -v`
Expected: pass.

- [ ] **Step 5: Run full suite to ensure no regression**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'follow' without conv-id tails per-identity inbox log"
```

---

### Task 18: CLI — `broker whoami`

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_whoami_prints_derived_identity(tmp_path: Path) -> None:
    import json as _json
    (tmp_path / "package.json").write_text(_json.dumps({"name": "test-pkg"}))
    result = subprocess.run(
        CLI + ["whoami"],
        cwd=tmp_path,
        env={"PATH": Path(sys.executable).parent.as_posix()},
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "test-pkg" in result.stdout
    assert str(tmp_path) in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_whoami_prints_derived_identity -v`
Expected: FAIL with unknown subcommand.

- [ ] **Step 3: Add the `whoami` subcommand**

```python
    who = subparsers.add_parser("whoami", help="Print the identity derived from cwd")
    who.set_defaults(func=_cmd_whoami)


def _cmd_whoami(args, sock_path: str) -> int:
    from broker_identity import derive_identity, IdentityDerivationError
    try:
        identity = derive_identity(Path.cwd())
    except IdentityDerivationError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{identity}  (from {Path.cwd()})")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_whoami_prints_derived_identity -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): CLI 'whoami' prints derived identity and cwd"
```

---

## Phase 4: Migration glue + integration test

### Task 19: Deprecation warnings on room commands

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Add failing test**

```python
def test_create_emits_deprecation_warning(broker) -> None:
    env = broker["env"]
    envargs = {"env": {**env, "PATH": Path(sys.executable).parent.as_posix()}, "capture_output": True, "text": True}
    result = subprocess.run(CLI + ["create", "--identity", "alice", "test-room"], **envargs)
    # Should succeed but emit a deprecation warning to stderr.
    assert result.returncode == 0
    assert "deprecat" in result.stderr.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_create_emits_deprecation_warning -v`
Expected: FAIL — no warning is emitted.

- [ ] **Step 3: Add deprecation warnings to `create`, `join`, `leave` command dispatch**

Find each of these subcommand handlers in `broker_cli.py` and prepend:

```python
    print(
        "warning: 'create' is deprecated. The room model is being replaced by DMs. "
        "Use 'broker send --to <identity>' instead. See broker skill docs.",
        file=sys.stderr,
    )
```

(Customize the message per command — mention `broker broadcast` for multi-party equivalents.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_create_emits_deprecation_warning -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): emit deprecation warnings on create/join/leave"
```

---

### Task 20: End-to-end integration test

**Files:**
- Create: `tests/test_broker_dm_e2e.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_broker_dm_e2e.py
"""End-to-end: a two-agent DM scenario running against a real broker server."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CLI = [sys.executable, str(SCRIPTS / "broker_cli.py")]


@pytest.fixture
def live_broker(tmp_path: Path):
    sock = tmp_path / "broker.sock"
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_STORAGE": str(tmp_path / "conversations"),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    proc = subprocess.Popen(CLI + ["server"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists(): break
        time.sleep(0.05)
    else:
        proc.terminate(); raise RuntimeError("server failed to start")
    yield {"env": env, "tmp": tmp_path}
    proc.terminate(); proc.wait(timeout=3)


def test_multi_party_dm_with_reply_all(live_broker) -> None:
    """Alice DMs [bob, carol]; bob replies-all; carol follows and sees both."""
    env = live_broker["env"]
    run = lambda *args: subprocess.run(CLI + list(args), env=env, capture_output=True, text=True, timeout=10)

    # Kickoff.
    sent = run("send", "--identity", "alice", "--to", "bob,carol", "kickoff message")
    assert sent.returncode == 0, sent.stderr
    kickoff_id = sent.stdout.strip()

    # Carol starts a follow with a short idle-timeout.
    follow = subprocess.Popen(
        CLI + ["follow", "--identity", "carol", "--idle-timeout", "2"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)

    # Bob replies-all.
    reply = run("reply-all", "--identity", "bob", "--to-message", kickoff_id, "replying to all")
    assert reply.returncode == 0, reply.stderr

    stdout, stderr = follow.communicate(timeout=5)
    assert "kickoff message" in stdout, stderr
    assert "replying to all" in stdout, stderr
    # Bob should NOT see his own reply-all in his inbox (no self-echo).
    bob_inbox = (live_broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "replying to all" not in bob_inbox
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_broker_dm_e2e.py -v`
Expected: pass (all building blocks are in place by this point).

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_e2e.py
git commit -m "test(broker): end-to-end DM + reply-all + follow scenario"
```

---

## Phase 5: Skill rewrite

### Task 21: Rewrite `skills/broker/SKILL.md`

**Files:**
- Modify: `skills/broker/SKILL.md`

- [ ] **Step 1: Write the new SKILL.md**

```markdown
---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, joining multi-agent conversations, or when the user asks you to talk to another agent. Use when you see references to the broker command or conversation IDs.
---

# Broker

A direct-message CLI for multi-agent conversations. Each agent has a persistent inbox; senders address specific recipients; messages are stored on disk regardless of the recipient's online state. `broker follow` drains your inbox and streams new messages as they arrive.

## Prerequisites

- The broker server must be running (`broker server` in a terminal).
- `Bash(broker:*)` must be in your `allowedTools`.

## Your identity

Every agent has a canonical identity derived from the project it runs in:

1. If the working directory contains `package.json`, the identity is that file's `name` field verbatim — e.g., `@proposit/shared`, `proposit-server`.
2. Otherwise, the identity is the `<org>/<repo>` pair from `git remote origin` — e.g., `Proposit-App/proposit-mobile`.

Run `broker whoami` to see your derived identity. The broker CLI fills `--identity` automatically when you omit it, so in most commands you can leave the flag off.

To address another agent, compute their identity the same way from their project. There is no directory to browse.

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker whoami` | Show the identity derived from cwd |
| `broker send --to <id>[,<id>] <content>` | Send a DM to one or more recipients |
| `broker broadcast <content>` | Fan out to every registered identity |
| `broker reply-all --to-message <msg-id> <content>` | Reply to all recipients of a prior DM |
| `broker follow [--idle-timeout N]` | **Block and stream your inbox** — drains backlog first, then live pushes |
| `broker history [--from <id>] [--since <iso>] [--sent]` | Read inbox (or outbox) without advancing the read-cursor |
| `broker read` | Read new inbox messages since last read; advances the cursor |

All commands exit non-zero on error with a message on stderr. Compact `<timestamp> [<sender>] <content>` is the default output format.

## Critical rules

1. **Use `broker follow` to wait for messages.** Do not write polling loops or `while true`. `broker follow` blocks until messages arrive, drains the backlog, and streams further messages in order.
2. **Do not `broker read` before `broker follow`.** `read` advances the cursor, so `follow` starts from empty. Use `follow` on its own.
3. **Do not parse broker output with `python`, `jq`, or similar.** The line format is designed for direct agent consumption.
4. **To reply to a broadcast, use `send --to <broadcaster>`, not `reply-all`.** Broadcasts have no stable recipient set, so `reply-all` on them is rejected.

## Canonical patterns

### Wait for a reply

```bash
broker send --to @proposit/shared "READY: 0.3.0 types final, publishing"
broker follow --idle-timeout 120
# ^ blocks, prints every incoming line, returns when the inbox quiets
```

### Announce to everyone

```bash
broker broadcast "BLOCKED: shared package build failed, all agents hold"
```

### Multi-party thread with reply-all

```bash
MID=$(broker send --to proposit-server,proposit-mobile "QUESTION: which schema to use?")
# Later, when someone replies:
broker reply-all --to-message $MID "DECISION: going with v2"
```

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference with flags and examples |
| `docs/patterns.md` | Canonical patterns: wait-for-reply, broadcasts, group threads |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) |
| `docs/troubleshooting.md` | Anti-patterns and why they're wrong |
| `docs/setup.md` | Installation, first-time setup, reserved identities |
```

- [ ] **Step 2: Commit**

```bash
git add skills/broker/SKILL.md
git commit -m "docs(broker): rewrite SKILL.md for DM model"
```

---

### Task 22: Rewrite `skills/broker/docs/usage.md`

**Files:**
- Modify: `skills/broker/docs/usage.md`

- [ ] **Step 1: Rewrite the file**

Write a full CLI reference covering every subcommand introduced in Phase 3 (`whoami`, `send`, `broadcast`, `reply-all`, `follow`, `history`, `read`). For each command, document:

- Synopsis line matching what `argparse` prints
- Purpose in one sentence
- Every flag with a one-line description
- One example invocation with expected output format

At the end, include a "Storage layout" section naming `~/.mcp-broker/inbox/<id>.log`, `outbox/`, `cursors/`, `identities.json`, and a one-line note that messages land in recipients' inboxes regardless of online status.

Include a "Legacy room commands" section at the bottom with a single sentence: "The `create`, `join`, `leave`, `members`, `close` commands remain for backwards compatibility but emit deprecation warnings. New work should use DMs exclusively."

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/usage.md
git commit -m "docs(broker): rewrite usage.md for DM subcommands"
```

---

### Task 23: Rewrite `skills/broker/docs/patterns.md`

**Files:**
- Modify: `skills/broker/docs/patterns.md`

- [ ] **Step 1: Rewrite**

Document the following patterns, each in its own section with a short rationale + runnable example:

1. **Wait for a reply** — `send` then `follow --idle-timeout`
2. **Announce to everyone** — `broadcast`
3. **Multi-party thread** — `send --to a,b,c` then `reply-all --to-message`
4. **Catch up after being away** — `history` (no cursor movement), `read` (advance cursor)
5. **Orchestrator watching many agents** — one `follow` on the orchestrator's own inbox captures every relay
6. **Streaming into Claude Code's Monitor tool** — point Monitor at `~/.mcp-broker/inbox/<identity>.log`

Each pattern should give the exact commands and note any pitfalls (e.g., "reply-all excludes yourself").

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/patterns.md
git commit -m "docs(broker): rewrite patterns.md for DM workflows"
```

---

### Task 24: Update `skills/broker/docs/troubleshooting.md`

**Files:**
- Modify: `skills/broker/docs/troubleshooting.md`

- [ ] **Step 1: Rewrite for DM-era anti-patterns**

Sections to include:

- **Writing a polling loop** — why wrong, what to do instead (`broker follow`)
- **`broker read` before `broker follow`** — desyncs the cursor; use `follow` alone
- **Parsing broker output with jq or python** — the line format is already agent-facing
- **Waiting on a BROADCAST via `reply-all`** — not supported; use `send --to <broadcaster>`
- **Reserved-identity errors** (`orchestrator is reserved...`) — what the token file is and when you need it
- **Identity mismatch** — if `--identity` differs from cwd derivation, broker uses what you passed; run `broker whoami` to confirm

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/troubleshooting.md
git commit -m "docs(broker): rewrite troubleshooting for DM anti-patterns"
```

---

### Task 25: Update `skills/broker/docs/signals.md`

**Files:**
- Modify: `skills/broker/docs/signals.md`

- [ ] **Step 1: Strip room-specific examples, keep signal vocabulary**

Edit the file to remove any mention of "room" / "conversation ID" from examples. Signal prefixes (`READY:` / `BLOCKED:` / `QUESTION:` / `DECISION:`) are unchanged — they're content conventions orthogonal to transport. Rewrite examples to use `broker send --to` or `broker broadcast`.

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/signals.md
git commit -m "docs(broker): signals.md examples use DM commands"
```

---

### Task 26: Update `skills/broker/docs/setup.md`

**Files:**
- Modify: `skills/broker/docs/setup.md`

- [ ] **Step 1: Update**

Add a new section **"Reserved identities"** covering:
- `orchestrator`, `human`, `BROADCAST` are reserved.
- To claim `orchestrator`, create `~/.mcp-broker/tokens/orchestrator.token` with any non-empty string and pass `--token` (or set `MCP_BROKER_TOKEN`) on the first connect. Same for `human`.
- Multi-workspace note: only one `orchestrator` per broker instance; scoped identities like `orchestrator:proposit-app` sidestep this.

Confirm the existing install steps still apply. Add an entry describing the new storage layout (`inbox/`, `outbox/`, `cursors/`, `identities.json`).

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/setup.md
git commit -m "docs(broker): setup.md covers reserved identities and DM storage layout"
```

---

## Phase 6: Release

### Task 27: Release notes + changelog

**Files:**
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`

- [ ] **Step 1: Read existing upcoming files to match style**

Run: `cat docs/release-notes/upcoming.md docs/changelogs/upcoming.md` (via `Read` tool).

- [ ] **Step 2: Add entries for the broker DM redesign**

To `docs/release-notes/upcoming.md` — a narrative paragraph explaining the shift: rooms → inboxes, deterministic identity derivation, `follow` now streams all incoming, `history` is cursor-free. Call out migration (room APIs deprecated but functional).

To `docs/changelogs/upcoming.md` — under an existing `### broker` section or a new one:

```markdown
### broker

- **added** `broker send --to`, `broadcast`, `reply-all`, `whoami` subcommands (DM model)
- **added** per-identity inbox/outbox logs under `~/.mcp-broker/inbox/` and `outbox/`
- **added** deterministic identity derivation from `package.json` or `git remote`
- **added** reserved identities `orchestrator` / `human` gated by token files
- **changed** `broker follow` without a conversation ID now tails the caller's inbox
- **changed** `broker read` without a conversation ID reads the caller's inbox
- **changed** `broker history` is a cursor-free peek; use `broker read` to advance
- **deprecated** `broker create` / `join` / `leave` — emit warnings; still functional
```

- [ ] **Step 3: Commit**

```bash
git add docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "docs: release notes and changelog for broker DM redesign"
```

---

### Task 28: Version bump + tag

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Check current version**

Run: `grep '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json`

- [ ] **Step 2: Bump to next minor version**

Per `CLAUDE.md`: "use minor for new skills or significant feature work." This is significant feature work on an existing skill — minor bump.

Edit both files to increment the minor version (e.g., `1.2.0` → `1.3.0`). Keep the patch component `.0`.

- [ ] **Step 3: Rename upcoming docs to versioned files**

```bash
VERSION=1.3.0  # substitute the actual new version
git mv docs/release-notes/upcoming.md docs/release-notes/v$VERSION.md
git mv docs/changelogs/upcoming.md docs/changelogs/v$VERSION.md
```

- [ ] **Step 4: Create empty new upcoming files**

```bash
# Use Write tool to create empty files — do NOT use bash redirects.
```

Use the `Write` tool to create `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` with a minimal header appropriate to this repo's convention (check a prior versioned file to match style).

- [ ] **Step 5: Commit and tag**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json \
        docs/release-notes/v$VERSION.md docs/changelogs/v$VERSION.md \
        docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "chore: release v$VERSION"
git tag v$VERSION
```

---

## Self-review

- **Spec coverage:** Each section of the design doc is addressed — identity derivation (T1), message format (T2), storage (T4), send/broadcast/reply-all (T6–T8), history/read (T9), reserved identities (T10), client (T11), CLI (T12–T18), deprecation (T19), end-to-end (T20), skill (T21–T26), release (T27–T28).
- **Open-question defaults:** Documented at top of plan; reflected in implementation (implicit registration via `registry.touch()` on every handler; per-host scoping via unchanged socket path; file-tailing `follow`; outbox log for sent visibility).
- **Type consistency:** `InboxLog.path_for` / `OutboxLog.path_for` / `CursorStore._path` use `encode_identity` consistently. `format_message` signature matches across server and client. `send_dm` / `send_broadcast` / `reply_all` / `history_inbox` / `read_inbox` are the four server request types referenced by both client and tests.
- **No placeholders:** Code blocks are complete per step. Docs rewrites (T22–T26) specify sections and content to include, since prose-writing tasks don't lend themselves to drop-in code blocks — content is described concretely enough that the executor can produce it without ambiguity.

---

## Execution

Plan complete and saved at `docs/plans/2026-04-22-broker-dm-redesign-implementation.md`.
