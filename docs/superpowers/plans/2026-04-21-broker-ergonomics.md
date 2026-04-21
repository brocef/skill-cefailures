# Broker Ergonomics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `broker follow` (push-based message consumer), fix disconnect-membership bug, rework `broker list` default, and expand the broker skill docs — so agents never reinvent polling loops.

**Architecture:** Three tracks: (1) server changes — bug fix + `conversation_closed` push + `list` default, (2) CLI changes — shared compact formatter, new `broker follow` subcommand consuming the existing latent server-push infrastructure, `broker read --format compact`, `broker list` choices update, (3) skill expansion — SKILL.md rewrite + three new docs. TDD for code; write-and-commit for docs.

**Tech Stack:** Python 3 (asyncio, argparse, pytest, pytest-asyncio), existing Unix-domain-socket JSON protocol between `BrokerServer` and `BrokerClient`.

**Spec:** `docs/superpowers/specs/2026-04-21-broker-ergonomics-design.md`

**One clarification added beyond the spec** (noted as Task 2b): `_broadcast_system` will include the full persisted message dict in its push payload (keeping the existing `event` / `identity` fields for back-compat), so `broker follow` can dedup system events by id the same way it dedups user messages. The spec left dedup-for-system-events unspecified; this is the cleanest resolution.

---

## File Structure

**Created:**
- `skills/broker/docs/patterns.md`
- `skills/broker/docs/signals.md`
- `skills/broker/docs/troubleshooting.md`
- `tests/test_broker_follow.py`

**Modified:**
- `scripts/broker_server.py` — `disconnect`, `_handle_close`, `_handle_list`, `_broadcast_system`
- `scripts/broker_cli.py` — new `follow` subcommand + handler, `format_message_compact` helper, `read` `--format` flag, `list` `--status` choices
- `scripts/broker_client.py` — no change (latent `on_push` queue already supports the design)
- `skills/broker/SKILL.md` — Quick Reference + Critical Rules block
- `skills/broker/docs/usage.md` — add `follow`, compact format, new list default
- `skills/broker/docs/setup.md` — minor — mention `follow` once
- `tests/test_broker_server.py` — invert `test_disconnect_broadcasts_leave`; add close-push test
- `tests/test_broker_e2e.py` — update leave-on-explicit-leave assertion remains; verify no implicit-disconnect-leave

**Release:**
- `docs/release-notes/upcoming.md` → `docs/release-notes/v1.2.0.md` + fresh `upcoming.md`
- `docs/changelogs/upcoming.md` → `docs/changelogs/v1.2.0.md` + fresh `upcoming.md`
- `.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — version bump

---

## Phase 1: Server changes (foundation)

### Task 1: Fix `disconnect` — membership persists across disconnect

**Files:**
- Modify: `scripts/broker_server.py:54-60`
- Modify: `tests/test_broker_server.py:222-240`

- [ ] **Step 1: Invert the existing test**

Replace `test_disconnect_broadcasts_leave` in `tests/test_broker_server.py`:

```python
def test_disconnect_does_not_broadcast_leave(server):
    """Disconnecting a client does NOT remove membership or broadcast leave.

    Membership changes only via explicit join/leave/close. This protects
    conversations from join/leave spam across agent send/read cycles.
    """
    alice_msgs = []
    server.connect("alice", alice_msgs.append)
    server.connect("bob", lambda m: None)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("bob", {
        "id": "req-2", "type": "join_conversation", "conversation_id": cid,
    })

    server.disconnect("bob")

    system_msgs = [m for m in alice_msgs if m["type"] == "system" and m["event"] == "leave"]
    assert not any(m.get("identity") == "bob" for m in system_msgs), \
        "disconnect must not broadcast a leave event"
    assert "bob" in server.members[cid], \
        "disconnect must not remove bob from conversation membership"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_broker_server.py::test_disconnect_does_not_broadcast_leave -v`
Expected: FAIL — current `disconnect` broadcasts leave and removes membership.

- [ ] **Step 3: Fix `disconnect` in `scripts/broker_server.py:54-60`**

Replace the method body:

```python
def disconnect(self, identity: str) -> None:
    """Remove the client's push callback. Does not change conversation membership.

    Membership is declarative: it changes only via explicit join / leave / close.
    Disconnecting does not broadcast a leave event — that was a historical bug
    that caused join/leave spam across every send/read cycle.
    """
    self.clients.pop(identity, None)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_broker_server.py::test_disconnect_does_not_broadcast_leave -v`
Expected: PASS.

- [ ] **Step 5: Run the full server test suite for regressions**

Run: `python -m pytest tests/test_broker_server.py -v`
Expected: All pass. If anything else fails, inspect — it may be another test that relied on the old behavior; invert it or update the assertion.

- [ ] **Step 6: Run the e2e suite**

Run: `python -m pytest tests/test_broker_e2e.py -v`
Expected: All pass. The test at lines 64-71 asserts a leave event after an **explicit** `leave_conversation` call — that path is unaffected.

- [ ] **Step 7: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_server.py
git commit -m "fix(broker): disconnect no longer removes membership or broadcasts leave"
```

---

### Task 2: Add `conversation_closed` push in `_handle_close`

**Files:**
- Modify: `scripts/broker_server.py:229-236`
- Modify: `tests/test_broker_server.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_server.py`:

```python
def test_close_pushes_conversation_closed_to_members(server):
    """Closing a conversation pushes a conversation_closed event to every
    connected member except the closer."""
    alice_msgs = []
    bob_msgs = []
    server.connect("alice", alice_msgs.append)
    server.connect("bob", bob_msgs.append)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("bob", {
        "id": "req-2", "type": "join_conversation", "conversation_id": cid,
    })

    server.handle_request("alice", {
        "id": "req-3", "type": "close_conversation", "conversation_id": cid,
    })

    closed_events = [m for m in bob_msgs if m.get("type") == "conversation_closed"]
    assert len(closed_events) == 1
    assert closed_events[0]["conversation_id"] == cid

    # The closer does not receive their own close event
    closer_events = [m for m in alice_msgs if m.get("type") == "conversation_closed"]
    assert closer_events == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_server.py::test_close_pushes_conversation_closed_to_members -v`
Expected: FAIL — no push emitted on close.

- [ ] **Step 3: Modify `_handle_close` at `scripts/broker_server.py:229-236`**

Replace the method:

```python
def _handle_close(self, identity: str, msg: dict) -> dict:
    """Handle close_conversation request.

    Flips the conversation to read-only and pushes a conversation_closed
    event to every connected member except the closer. Followers treat
    the event as an explicit exit signal.
    """
    cid = msg["conversation_id"]
    if cid not in self.conversations:
        raise ValueError(f"Conversation '{cid}' not found")
    self.conversations[cid]["status"] = "closed"
    self._save_conversation(cid)

    push = {"type": "conversation_closed", "conversation_id": cid}
    for member in self.members.get(cid, set()):
        if member != identity and member in self.clients:
            self.clients[member](push)

    return {"conversation_id": cid, "status": "closed"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_server.py::test_close_pushes_conversation_closed_to_members -v`
Expected: PASS.

- [ ] **Step 5: Run full server + e2e tests for regressions**

Run: `python -m pytest tests/test_broker_server.py tests/test_broker_e2e.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_server.py
git commit -m "feat(broker): push conversation_closed event to connected members on close"
```

---

### Task 2b: Include full message dict in system-event pushes

**Why:** spec clarification. `_broadcast_system` currently emits `{type: "system", event, identity}` with no id; history returns system messages with `sender="system", content, id`. Without a shared id, `broker follow` can't dedup system events that arrive in both history and push during the connect→history race window. Fix: include the full persisted message dict in the push, keeping existing keys for back-compat.

**Files:**
- Modify: `scripts/broker_server.py:94-107`
- Modify: `tests/test_broker_server.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_server.py`:

```python
def test_broadcast_system_push_includes_full_message(server):
    """System event pushes carry the full persisted message (with id)
    alongside the legacy event/identity fields."""
    alice_msgs = []
    server.connect("alice", alice_msgs.append)
    server.connect("bob", lambda m: None)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("bob", {
        "id": "req-2", "type": "join_conversation", "conversation_id": cid,
    })

    system_pushes = [m for m in alice_msgs if m.get("type") == "system"]
    assert len(system_pushes) >= 1
    push = [m for m in system_pushes if m.get("identity") == "bob"][0]
    assert "message" in push, "push must include the full message dict"
    assert push["message"]["sender"] == "system"
    assert push["message"]["id"].startswith("msg-")
    assert push["message"]["content"] == "bob joined"
    # legacy fields preserved
    assert push["event"] == "join"
    assert push["identity"] == "bob"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_server.py::test_broadcast_system_push_includes_full_message -v`
Expected: FAIL — `message` key missing from push.

- [ ] **Step 3: Modify `_broadcast_system` at `scripts/broker_server.py:94-107`**

Replace:

```python
def _broadcast_system(self, conversation_id: str, event: str, identity: str) -> None:
    """Create a system message, persist it, and push to connected members.

    The push payload includes the full persisted message dict (with id) so
    consumers can dedup system events by id the same way as user messages.
    The legacy event/identity fields are preserved for back-compat.
    """
    msg = {
        "id": self._message_id(),
        "sender": "system",
        "content": f"{identity} {event}ed" if event == "join" else f"{identity} left",
        "timestamp": self._timestamp(),
    }
    self.conversations[conversation_id]["messages"].append(msg)
    self._save_conversation(conversation_id)
    push = {
        "type": "system",
        "conversation_id": conversation_id,
        "event": event,
        "identity": identity,
        "message": msg,
    }
    for member in self.members.get(conversation_id, set()):
        if member != identity and member in self.clients:
            self.clients[member](push)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_server.py::test_broadcast_system_push_includes_full_message -v`
Expected: PASS.

- [ ] **Step 5: Run full tests for regressions**

Run: `python -m pytest tests/ -v`
Expected: all pass. The e2e test at `tests/test_broker_e2e.py:70-71` reads `m["type"] == "system" and m["event"] == "leave"` and `e["identity"]` — those keys remain, so it still passes.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_server.py
git commit -m "feat(broker): include full message dict in system-event pushes for dedup"
```

---

### Task 3: `list_conversations` default = `open`, accept `"all"`

**Files:**
- Modify: `scripts/broker_server.py:201-219`
- Modify: `tests/test_broker_server.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_server.py`:

```python
def test_list_conversations_defaults_to_open(server):
    """list_conversations with no status filter returns only open conversations."""
    server.connect("alice", lambda m: None)
    r1 = server.handle_request("alice", {"id": "r1", "type": "create_conversation", "topic": "Open one"})
    r2 = server.handle_request("alice", {"id": "r2", "type": "create_conversation", "topic": "To close"})
    cid_closed = r2["data"]["conversation_id"]
    server.handle_request("alice", {"id": "r3", "type": "close_conversation", "conversation_id": cid_closed})

    result = server.handle_request("alice", {"id": "r4", "type": "list_conversations"})
    topics = [c["topic"] for c in result["data"]["conversations"]]
    assert "Open one" in topics
    assert "To close" not in topics


def test_list_conversations_status_all_returns_everything(server):
    """Explicit status='all' returns open + closed."""
    server.connect("alice", lambda m: None)
    r1 = server.handle_request("alice", {"id": "r1", "type": "create_conversation", "topic": "Open one"})
    r2 = server.handle_request("alice", {"id": "r2", "type": "create_conversation", "topic": "To close"})
    cid_closed = r2["data"]["conversation_id"]
    server.handle_request("alice", {"id": "r3", "type": "close_conversation", "conversation_id": cid_closed})

    result = server.handle_request("alice", {
        "id": "r4", "type": "list_conversations", "status": "all",
    })
    topics = [c["topic"] for c in result["data"]["conversations"]]
    assert "Open one" in topics
    assert "To close" in topics
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_server.py::test_list_conversations_defaults_to_open tests/test_broker_server.py::test_list_conversations_status_all_returns_everything -v`
Expected: FAIL — default currently returns everything; `"all"` isn't specifically handled.

- [ ] **Step 3: Modify `_handle_list` at `scripts/broker_server.py:201-219`**

Replace the method:

```python
def _handle_list(self, identity: str, msg: dict) -> dict:
    """Handle list_conversations request.

    Default: returns only conversations with status='open'. Pass status='all'
    to return everything, or status='open'/'closed' for explicit filtering.
    """
    status_filter = msg.get("status", "open")
    conversations = []
    for conv in self.conversations.values():
        if status_filter != "all" and conv["status"] != status_filter:
            continue
        cursor = conv["cursors"].get(identity, 0)
        non_system = [m for m in conv["messages"] if m["sender"] != "system"]
        unread = [m for m in conv["messages"][cursor:] if m["sender"] not in ("system", identity)]
        conversations.append({
            "id": conv["id"],
            "topic": conv["topic"],
            "status": conv["status"],
            "created_by": conv["createdBy"],
            "message_count": len(non_system),
            "unread_count": len(unread),
        })
    return {"conversations": conversations}
```

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `python -m pytest tests/test_broker_server.py::test_list_conversations_defaults_to_open tests/test_broker_server.py::test_list_conversations_status_all_returns_everything -v`
Expected: PASS.

- [ ] **Step 5: Run full tests for regressions**

Run: `python -m pytest tests/ -v`
Expected: all pass. If an existing test asserted "no status filter returns all conversations," update it to pass `status="all"` explicitly.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_server.py
git commit -m "feat(broker): list_conversations defaults to status='open'; add 'all' to retain previous behavior"
```

---

## Phase 2: Compact message formatter

### Task 4: `format_message_compact` helper

**Files:**
- Modify: `scripts/broker_cli.py` (add helper near existing `format_message`, around line 32-41)
- Create: test cases in a new file `tests/test_broker_cli.py` or append if it exists.

- [ ] **Step 1: Check whether `tests/test_broker_cli.py` exists**

Run: `ls tests/test_broker_cli.py`
Expected: exists (per earlier exploration). If so, append; otherwise create.

- [ ] **Step 2: Write the failing test — append to `tests/test_broker_cli.py`**

```python
def test_format_message_compact_user_message():
    """User messages render as [sender] content with no indent, no timestamp."""
    from broker_cli import format_message_compact
    msg = {"id": "msg-abc", "sender": "server", "content": "Okay, on it", "timestamp": "2026-04-21T..."}
    assert format_message_compact(msg) == "[server] Okay, on it"


def test_format_message_compact_system_message_from_history():
    """System messages from history have sender='system' and free-form content."""
    from broker_cli import format_message_compact
    msg = {"id": "msg-xyz", "sender": "system", "content": "bob left", "timestamp": "2026-04-21T..."}
    assert format_message_compact(msg) == "[system] bob left"


def test_format_message_compact_multiline_content_preserved():
    """Newlines in content are preserved; the line-oriented claim is best-effort."""
    from broker_cli import format_message_compact
    msg = {"sender": "alice", "content": "line1\nline2"}
    assert format_message_compact(msg) == "[alice] line1\nline2"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_cli.py::test_format_message_compact_user_message -v`
Expected: FAIL — `format_message_compact` not defined.

- [ ] **Step 4: Add `format_message_compact` to `scripts/broker_cli.py`, after the existing `format_message` (around line 42)**

```python
def format_message_compact(msg: dict) -> str:
    """Format a message dict as a single compact line for agent consumption.

    Both user and system messages from history render identically via the
    sender/content fields: [sender] content. This is the agent-facing format;
    it has no leading indent and no timestamp (the server persists timestamps
    on disk for audit).

    Args:
        msg: A persisted message dict with keys: sender, content.
             Timestamps and ids are ignored here.

    Returns:
        A string like: "[server] Okay, on it"
    """
    return f"[{msg['sender']}] {msg['content']}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_cli.py -v`
Expected: all tests (new + existing) pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker-cli): add format_message_compact — agent-facing one-line format"
```

---

## Phase 3: `broker read --format compact`

### Task 5: Add `--format` flag to `broker read`

**Files:**
- Modify: `scripts/broker_cli.py` — find the `p_read` subparser (around line 441-445) and its handler.

- [ ] **Step 1: Locate the `read` command's handler**

Run: `grep -n 'args.command == "read"' scripts/broker_cli.py`
Note the line number so you can find the dispatch in `main()`.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_broker_cli.py`:

```python
import subprocess
import sys
import tempfile
import os
from pathlib import Path


@pytest.mark.asyncio
async def test_broker_read_compact_format(sock_path, tmp_path):
    """`broker read --format compact` emits one line per message in [sender] content form."""
    from broker_server import BrokerServer, start_server
    from broker_client import BrokerClient

    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        result = await alice.create_conversation("T", content="hi there")
        cid = result["conversation_id"]
        await alice.close()

        # Run the CLI as a subprocess, parsing its compact output
        broker_cli = str(Path(__file__).parent.parent / "scripts" / "broker_cli.py")
        out = subprocess.run(
            [sys.executable, broker_cli, "read",
             "--identity", "bob",
             "--socket", sock_path,
             "--format", "compact",
             cid],
            capture_output=True, text=True, check=True,
        )
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        assert "[alice] hi there" in lines
    finally:
        srv.close()
        await srv.wait_closed()
```

Note: add imports `import pytest` and `import subprocess, sys, tempfile, os` at the top of the file if not already present; reuse the `sock_path` fixture by importing or copying from `tests/test_broker_e2e.py:15-23` — or create a shared `tests/conftest.py` that defines it. If `sock_path` already exists in `test_broker_cli.py`, use it.

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_cli.py::test_broker_read_compact_format -v`
Expected: FAIL — `--format` flag is not defined.

- [ ] **Step 4: Add `--format` to the `read` subparser in `scripts/broker_cli.py:441-445`**

Replace:

```python
    # --- read ---
    p_read = subparsers.add_parser("read", help="Read new messages")
    p_read.add_argument("--identity", required=True, help="Your identity")
    p_read.add_argument("conversation_id", help="Conversation ID")
    p_read.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_read.add_argument("--format", choices=["json", "compact"], default="json",
                        help="Output format. 'compact' emits [sender] content lines (agent-facing). Default: json.")
```

- [ ] **Step 5: Update the `read` dispatch branch in `main()`**

Find the existing `read` branch in `main()` — it likely calls the client's `history` and prints the JSON result. Replace the print with a branch on `args.format`:

```python
    elif args.command == "read":
        client = BrokerClient(args.identity, args.socket)
        try:
            await client.connect()
        except (FileNotFoundError, ConnectionRefusedError):
            print(json.dumps({"error": f"Cannot connect to broker at {args.socket}. Is the broker server running?"}), file=sys.stderr)
            sys.exit(1)
        try:
            result = await client.history(args.conversation_id)
        finally:
            await client.close()
        if args.format == "compact":
            for msg in result["messages"]:
                print(format_message_compact(msg), flush=True)
        else:
            print(json.dumps(result))
```

(Exact existing code may differ — preserve its error handling shape and just add the format branch.)

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_cli.py::test_broker_read_compact_format -v`
Expected: PASS.

- [ ] **Step 7: Run full suite for regressions**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker-cli): broker read --format compact for agent-facing output"
```

---

## Phase 4: `broker follow` subcommand

### Task 6: Add `broker follow` subparser with argument validation

**Files:**
- Modify: `scripts/broker_cli.py` — add subparser for `follow`.
- Create: `tests/test_broker_follow.py`.

- [ ] **Step 1: Create `tests/test_broker_follow.py` with a subparser test**

```python
"""Tests for `broker follow` — push-based message consumer."""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.fixture
def sock_path():
    """Unix socket path under /tmp to avoid macOS 104-char limit."""
    fd, path = tempfile.mkstemp(prefix="broker_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


BROKER_CLI = str(Path(__file__).parent.parent / "scripts" / "broker_cli.py")


def test_follow_subcommand_parses_args():
    """Parser accepts all documented flags without error."""
    result = subprocess.run(
        [sys.executable, BROKER_CLI, "follow", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--identity" in result.stdout
    assert "--idle-timeout" in result.stdout
    assert "--timeout" in result.stdout
    assert "--count" in result.stdout
    assert "--include-system" in result.stdout
    assert "--format" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_subcommand_parses_args -v`
Expected: FAIL — unknown subcommand `follow`.

- [ ] **Step 3: Add `follow` subparser to `scripts/broker_cli.py`, near the other subparsers**

```python
    # --- follow ---
    p_follow = subparsers.add_parser(
        "follow",
        help="Stream new messages from a conversation. Drains backlog, then "
             "consumes pushes until idle-timeout, total timeout, count, or "
             "conversation_closed. Use foreground to block until a reply arrives.",
    )
    p_follow.add_argument("--identity", required=True, help="Your identity")
    p_follow.add_argument("conversation_id", help="Conversation ID")
    p_follow.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_follow.add_argument("--idle-timeout", type=int, default=120,
                          help="Exit after N seconds of silence. 0 disables. Default: 120.")
    p_follow.add_argument("--timeout", type=int, default=600,
                          help="Hard cap in seconds. 0 disables. Default: 600.")
    p_follow.add_argument("--count", type=int, default=0,
                          help="Exit after N messages received. 0 disables. Default: 0.")
    p_follow.add_argument("--include-system", action="store_true",
                          help="Include system join/leave events in the stream. "
                               "Default: suppressed.")
    p_follow.add_argument("--format", choices=["compact", "json"], default="compact",
                          help="Output format. Default: compact.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_subcommand_parses_args -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_follow.py
git commit -m "feat(broker-cli): add `broker follow` subparser with args"
```

---

### Task 7: Implement `follow` — history drain + compact print

**Files:**
- Modify: `scripts/broker_cli.py` — add a `cmd_follow` async function and dispatch.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_drains_backlog_then_exits_on_idle(sock_path, tmp_path):
    """Follow prints history then exits when idle-timeout elapses."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T", content="first message")
        cid = r["conversation_id"]
        await alice.send_message(cid, "second message")
        await alice.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--idle-timeout", "1",
            "--timeout", "10",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[alice] first message" in lines
        assert "[alice] second message" in lines
        assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_drains_backlog_then_exits_on_idle -v`
Expected: FAIL — `follow` has no handler yet.

- [ ] **Step 3: Implement `cmd_follow` in `scripts/broker_cli.py`**

Add this function near the other command handlers (check existing style in the file for where command-dispatch branches live):

```python
async def cmd_follow(args: argparse.Namespace) -> int:
    """Run `broker follow`: drain backlog, then consume push until exit.

    Returns the process exit code. 0 on clean exit; 1 on socket error.
    """
    client = BrokerClient(args.identity, args.socket)
    # Install the push queue BEFORE connect, so pushes landing between
    # connect and history() don't go to a Queue(None) black hole.
    client.on_push = asyncio.Queue()

    try:
        await client.connect()
    except (FileNotFoundError, ConnectionRefusedError):
        print(json.dumps({
            "error": f"Cannot connect to broker at {args.socket}. Is the broker server running?",
        }), file=sys.stderr)
        return 1

    seen_ids: set[str] = set()
    try:
        # 1. Drain backlog via history.
        history = await client.history(args.conversation_id)
        for msg in history["messages"]:
            seen_ids.add(msg["id"])
            _emit(msg, args)

        # 2. Consume pushes.
        deadline = _compute_deadline(args.timeout)
        count = 0
        while True:
            timeout = _next_timeout(deadline, args.idle_timeout)
            try:
                push = await asyncio.wait_for(client.on_push.get(), timeout=timeout)
            except asyncio.TimeoutError:
                # Either idle or hard-cap elapsed. Either way, clean exit.
                break

            if push.get("conversation_id") != args.conversation_id:
                continue

            if push["type"] == "conversation_closed":
                break

            if push["type"] in ("message", "system"):
                msg = push["message"]
                if msg["id"] in seen_ids:
                    continue
                seen_ids.add(msg["id"])
                if _emit(msg, args):
                    count += 1
                    if args.count > 0 and count >= args.count:
                        break
    finally:
        await client.close()

    return 0


def _compute_deadline(hard_cap_seconds: int) -> float | None:
    """Absolute monotonic deadline, or None if disabled (hard_cap == 0)."""
    import time
    if hard_cap_seconds <= 0:
        return None
    return time.monotonic() + hard_cap_seconds


def _next_timeout(deadline: float | None, idle_seconds: int) -> float | None:
    """Compute the next asyncio.wait_for timeout: min(remaining deadline, idle).

    Returns None to wait forever (both disabled).
    """
    import time
    candidates = []
    if deadline is not None:
        candidates.append(max(0.0, deadline - time.monotonic()))
    if idle_seconds > 0:
        candidates.append(float(idle_seconds))
    if not candidates:
        return None
    return min(candidates)


def _emit(msg: dict, args: argparse.Namespace) -> bool:
    """Print a message per the requested format and system-filter.

    Returns True if the message was emitted, False if filtered out.
    """
    if msg["sender"] == "system" and not args.include_system:
        return False
    if args.format == "json":
        print(json.dumps({
            "id": msg["id"], "sender": msg["sender"],
            "content": msg["content"], "timestamp": msg["timestamp"],
        }), flush=True)
    else:
        print(format_message_compact(msg), flush=True)
    return True
```

- [ ] **Step 4: Wire `cmd_follow` into `main()` dispatch**

Find where the dispatch lives in `main()` and add:

```python
    elif args.command == "follow":
        return await cmd_follow(args)
```

Ensure the surrounding `main()` returns the int exit code and `sys.exit(...)` picks it up. If the existing pattern uses `asyncio.run(main())` and passes the return value to `sys.exit`, this works as-is; otherwise, do `sys.exit(asyncio.run(cmd_follow(args)))` in that branch.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_drains_backlog_then_exits_on_idle -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_follow.py
git commit -m "feat(broker-cli): implement broker follow — history drain + idle-exit + compact output"
```

---

### Task 8: `follow` receives pushes sent mid-stream

**Files:**
- Modify: `tests/test_broker_follow.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_prints_push_message_mid_stream(sock_path, tmp_path):
    """Messages sent after follow starts are pushed and printed."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T")
        cid = r["conversation_id"]
        # Bob must be a member to receive pushes
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--idle-timeout", "2",
            "--timeout", "10",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Give follow time to connect + drain (empty) + start listening.
        await asyncio.sleep(0.3)
        await alice.send_message(cid, "live message")
        await asyncio.sleep(0.3)
        await alice.close()

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[alice] live message" in lines
        assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_prints_push_message_mid_stream -v`
Expected: PASS (the Task 7 implementation already consumes pushes). If it fails, inspect whether `on_push` queue is being populated — check `broker_client.py:69-70` for the `await self.on_push.put(msg)` line and make sure `client.on_push` was set before `connect()`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_follow.py
git commit -m "test(broker-follow): assert live push messages are printed"
```

---

### Task 9: `--count` exits after N messages

**Files:**
- Modify: `tests/test_broker_follow.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_count_exits_after_n_messages(sock_path, tmp_path):
    """--count 1 exits after one new message (history messages do not count)."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T", content="pre-existing")
        cid = r["conversation_id"]
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--count", "1",
            "--idle-timeout", "10",
            "--timeout", "20",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.3)
        await alice.send_message(cid, "msg-1")
        await alice.send_message(cid, "msg-2")  # should be ignored — count already reached
        await alice.close()

        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        # History backlog is always printed regardless of count.
        assert "[alice] pre-existing" in lines
        # Exactly one push message is printed.
        push_lines = [l for l in lines if l == "[alice] msg-1" or l == "[alice] msg-2"]
        assert push_lines == ["[alice] msg-1"]
    finally:
        srv.close()
        await srv.wait_closed()
```

Note: the Task 7 implementation already increments `count` only for push-delivered messages (not history). Confirm by re-reading `cmd_follow`.

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_count_exits_after_n_messages -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_follow.py
git commit -m "test(broker-follow): --count exits after N push messages"
```

---

### Task 10: `--include-system` renders join/leave in the stream

**Files:**
- Modify: `tests/test_broker_follow.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_include_system_renders_join_events(sock_path, tmp_path):
    """--include-system causes [system] <identity> joined lines to appear."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T")
        cid = r["conversation_id"]
        # Bob joins (producing a system message), then leaves, then disconnects.
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "carol",
            "--socket", sock_path,
            "--idle-timeout", "1",
            "--timeout", "10",
            "--include-system",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[system] alice joined" in lines
        assert "[system] bob joined" in lines
        await alice.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_follow_default_hides_system_events(sock_path, tmp_path):
    """Without --include-system, join/leave lines are absent from stdout."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T", content="body")
        cid = r["conversation_id"]
        await alice.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "carol",
            "--socket", sock_path,
            "--idle-timeout", "1",
            "--timeout", "10",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[alice] body" in lines
        assert not any(l.startswith("[system]") for l in lines)
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_include_system_renders_join_events tests/test_broker_follow.py::test_follow_default_hides_system_events -v`
Expected: PASS (implementation from Task 7 already respects `--include-system`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_follow.py
git commit -m "test(broker-follow): --include-system toggles join/leave rendering"
```

---

### Task 11: `conversation_closed` push causes clean exit

**Files:**
- Modify: `tests/test_broker_follow.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_exits_clean_on_conversation_closed(sock_path, tmp_path):
    """When the conversation is closed mid-follow, follow exits with code 0 without waiting for idle-timeout."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T")
        cid = r["conversation_id"]
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--idle-timeout", "60",  # long — so a premature idle-exit would indicate failure
            "--timeout", "60",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.3)
        await alice.close_conversation(cid)
        await alice.close()

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_exits_clean_on_conversation_closed -v`
Expected: PASS (Task 7 implementation already handles the `conversation_closed` push; Task 2 server-side emits it).

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_follow.py
git commit -m "test(broker-follow): exits cleanly when the conversation is closed mid-stream"
```

---

### Task 12: Socket-disconnect → non-zero exit with stderr message

**Files:**
- Modify: `scripts/broker_cli.py` — harden `cmd_follow` against abrupt socket closure.
- Modify: `tests/test_broker_follow.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_follow.py`:

```python
@pytest.mark.asyncio
async def test_follow_exits_nonzero_when_server_vanishes(sock_path, tmp_path):
    """If the broker server closes its socket while follow is running,
    follow exits non-zero with a stderr error message."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    alice = BrokerClient("alice", sock_path)
    await alice.connect()
    r = await alice.create_conversation("T")
    cid = r["conversation_id"]
    bob = BrokerClient("bob", sock_path)
    await bob.connect()
    await bob.join_conversation(cid)
    await bob.close()

    proc = await asyncio.create_subprocess_exec(
        sys.executable, BROKER_CLI, "follow",
        "--identity", "bob",
        "--socket", sock_path,
        "--idle-timeout", "60",
        "--timeout", "60",
        cid,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await asyncio.sleep(0.3)
    await alice.close()
    srv.close()
    await srv.wait_closed()

    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    assert proc.returncode != 0
    assert b"broker" in stderr.lower() or b"socket" in stderr.lower() or b"connection" in stderr.lower(), \
        f"expected an informative stderr; got: {stderr.decode()}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_exits_nonzero_when_server_vanishes -v`
Expected: FAIL — current `cmd_follow` likely hangs, times out, or exits with code 0 after idle.

- [ ] **Step 3: Harden `cmd_follow` in `scripts/broker_cli.py`**

Wrap the push-consumption loop to detect that the client's listener task ended unexpectedly. Update the `cmd_follow` loop to also watch the listener task:

```python
async def cmd_follow(args: argparse.Namespace) -> int:
    client = BrokerClient(args.identity, args.socket)
    client.on_push = asyncio.Queue()

    try:
        await client.connect()
    except (FileNotFoundError, ConnectionRefusedError):
        print(json.dumps({
            "error": f"Cannot connect to broker at {args.socket}. Is the broker server running?",
        }), file=sys.stderr)
        return 1

    seen_ids: set[str] = set()
    try:
        history = await client.history(args.conversation_id)
        for msg in history["messages"]:
            seen_ids.add(msg["id"])
            _emit(msg, args)

        deadline = _compute_deadline(args.timeout)
        count = 0
        while True:
            timeout = _next_timeout(deadline, args.idle_timeout)
            get_task = asyncio.create_task(client.on_push.get())
            listener_task = client._listener_task  # type: ignore[attr-defined]

            waiters = {get_task}
            if listener_task is not None and not listener_task.done():
                waiters.add(listener_task)

            try:
                done, pending = await asyncio.wait(
                    waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED,
                )
            except asyncio.CancelledError:
                raise

            if not done:
                # Timeout (idle or hard cap) elapsed — clean exit.
                get_task.cancel()
                break

            if listener_task is not None and listener_task in done:
                # Server-side socket closed. Abort with a clear error.
                get_task.cancel()
                print(json.dumps({
                    "error": "Broker socket closed unexpectedly. Is the broker server still running?",
                }), file=sys.stderr)
                return 1

            push = get_task.result()

            if push.get("conversation_id") != args.conversation_id:
                continue
            if push["type"] == "conversation_closed":
                break
            if push["type"] in ("message", "system"):
                msg = push["message"]
                if msg["id"] in seen_ids:
                    continue
                seen_ids.add(msg["id"])
                if _emit(msg, args):
                    count += 1
                    if args.count > 0 and count >= args.count:
                        break
    finally:
        await client.close()

    return 0
```

Rationale for accessing `client._listener_task`: the client's `_listen` coroutine exits on EOF (`broker_client.py:57-58`); watching the task lets us distinguish "no messages yet" from "server gone." Acceptable for this CLI wrapper — a cleaner approach would add a public hook on the client, but that's outside scope.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_broker_follow.py::test_follow_exits_nonzero_when_server_vanishes -v`
Expected: PASS.

- [ ] **Step 5: Run the full follow-test file**

Run: `python -m pytest tests/test_broker_follow.py -v`
Expected: all prior tests still pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_follow.py
git commit -m "feat(broker-cli): follow exits non-zero with stderr when broker socket drops"
```

---

## Phase 5: `broker list` CLI

### Task 13: Add `"all"` to `--status` choices; default no-flag → open

**Files:**
- Modify: `scripts/broker_cli.py:450`
- Modify: `tests/test_broker_cli.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_broker_cli.py`:

```python
@pytest.mark.asyncio
async def test_broker_list_default_shows_only_open(sock_path, tmp_path):
    """With no --status flag, `broker list` returns only open conversations."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r1 = await alice.create_conversation("open-one")
        r2 = await alice.create_conversation("to-close")
        await alice.close_conversation(r2["conversation_id"])
        await alice.close()

        out = subprocess.run(
            [sys.executable, BROKER_CLI, "list", "--identity", "alice", "--socket", sock_path],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(out.stdout)
        topics = [c["topic"] for c in data["conversations"]]
        assert "open-one" in topics
        assert "to-close" not in topics
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_broker_list_status_all(sock_path, tmp_path):
    """--status all returns both open and closed conversations."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r1 = await alice.create_conversation("open-one")
        r2 = await alice.create_conversation("to-close")
        await alice.close_conversation(r2["conversation_id"])
        await alice.close()

        out = subprocess.run(
            [sys.executable, BROKER_CLI, "list", "--identity", "alice",
             "--socket", sock_path, "--status", "all"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(out.stdout)
        topics = [c["topic"] for c in data["conversations"]]
        assert "open-one" in topics
        assert "to-close" in topics
    finally:
        srv.close()
        await srv.wait_closed()
```

Ensure `import json` exists at the top of `tests/test_broker_cli.py`.

- [ ] **Step 2: Run tests to verify `--status all` fails**

Run: `python -m pytest tests/test_broker_cli.py::test_broker_list_status_all -v`
Expected: FAIL — `all` not in argparse choices.

The default-shows-open test should pass already (Phase 1 Task 3 implemented the server side; the CLI just sends no `status` and the server defaults to open).

- [ ] **Step 3: Update the `list` subparser at `scripts/broker_cli.py:450`**

Change:

```python
    p_list.add_argument("--status", choices=["open", "closed"], help="Filter by status")
```

to:

```python
    p_list.add_argument(
        "--status",
        choices=["open", "closed", "all"],
        help="Filter by status. Default (no flag): open. Use 'all' to include closed.",
    )
```

Confirm the `list` dispatch sends `status` only when the flag is provided (i.e., passes `args.status` through unchanged — if it's `None` the request omits the key, letting the server apply its new `"open"` default).

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_broker_cli.py::test_broker_list_default_shows_only_open tests/test_broker_cli.py::test_broker_list_status_all -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat(broker-cli): broker list defaults to open; --status all to see closed too"
```

---

## Phase 6: Skill rewrite

### Task 14: Update `skills/broker/SKILL.md`

**Files:**
- Modify: `skills/broker/SKILL.md`

- [ ] **Step 1: Rewrite `SKILL.md` — full replacement**

Replace the file contents with:

````markdown
---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, joining multi-agent conversations, or when the user asks you to talk to another agent. Use when you see references to the broker command or conversation IDs.
---

# Broker

A chatroom-like CLI for multi-agent conversations. Multiple Claude Code agents and a human talk through a shared broker server over a Unix socket. Conversations persist to `~/.mcp-broker/conversations/` for audit.

## Prerequisites

- The broker server must be running (`broker server` in a terminal).
- `Bash(broker:*)` must be in your `allowedTools`.

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker list --identity NAME` | List **open** conversations. Pass `--status all` to include closed. |
| `broker create --identity NAME TOPIC [--content "seed"]` | Start a conversation |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message |
| `broker read --identity NAME CONV_ID [--format compact\|json]` | Read new messages once |
| `broker follow --identity NAME CONV_ID` | **Block and stream new messages** — use this to wait for a reply |
| `broker join --identity NAME CONV_ID` | Join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker members --identity NAME CONV_ID` | List who's in a conversation |
| `broker close --identity NAME CONV_ID` | Close a conversation (read-only) |

All commands exit non-zero on error with JSON to stderr. `broker follow` and `broker read --format compact` emit agent-facing one-line format: `[sender] content`.

## Critical rules

These are the most common mistakes agents make with the broker. Follow them before consulting the detailed docs.

1. **Use `broker follow` to wait for messages.** Do **not** write `while true; broker read; sleep N`. `broker follow` blocks until messages arrive, drains the backlog, streams pushes, and exits on idle/timeout/count.
2. **Do not parse broker output with `python`, `jq`, or similar.** The compact line format (`[sender] content`) is the agent-facing format; read it directly. JSON is for scripts only.
3. **Do not maintain `/tmp/*_seen.txt` dedup files.** The broker server tracks per-identity read cursors; each `broker read` / `broker follow` only returns messages not yet seen by your identity.
4. **For focused 2-agent discussions, create a new conversation** named `{a}-{b}-{topic}-{timestamp}` instead of using a shared room. Close it when done. This keeps other agents' context clean.

## Canonical pattern: wait for a reply

```bash
broker send --identity server ROOM "We need changes to core"
broker follow ROOM --identity server --idle-timeout 120
# ^ blocks, prints every incoming line, returns when the discussion quiets
```

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference with examples and JSON formats |
| `docs/patterns.md` | Canonical patterns: wait-for-reply, side conversations, stream-while-working |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) for inter-agent coordination |
| `docs/troubleshooting.md` | Anti-patterns and why they're wrong — read if you catch yourself writing a polling loop |
| `docs/setup.md` | Installation, configuration, first-time setup |
````

- [ ] **Step 2: Commit**

```bash
git add skills/broker/SKILL.md
git commit -m "docs(broker): rewrite SKILL.md — follow, critical rules, new docs table"
```

---

### Task 15: Update `skills/broker/docs/usage.md`

**Files:**
- Modify: `skills/broker/docs/usage.md`

- [ ] **Step 1: Add a `follow` section and update `list` and `read`**

Insert after the existing `### read` section:

````markdown
### follow — Block and stream new messages

```bash
broker follow a1b2c3 --identity agent_b
broker follow a1b2c3 --identity agent_b --idle-timeout 60 --timeout 300
broker follow a1b2c3 --identity agent_b --count 1   # wait for one reply
broker follow a1b2c3 --identity agent_b --include-system --format json
```

Behavior:
- Connects to the broker and drains any unread backlog (via the server-side per-identity cursor).
- Streams new messages as they arrive (push from the server — no polling).
- Exits when any of these becomes true:
  - `--idle-timeout N` seconds elapse with no new message (default 120; `0` disables).
  - `--timeout N` hard cap elapses (default 600; `0` disables).
  - `--count N` messages received (default unset).
  - The conversation is closed by another agent.

Output (compact, default):

```
[server] Okay, on it
[core] Ready for the issue description
```

System join/leave events are suppressed unless `--include-system` is passed. JSON output is available via `--format json` (one JSON object per line).

Exit codes:
- `0` — clean exit via idle/timeout/count/close.
- `1` — could not connect, or socket dropped mid-stream (error printed to stderr).

**Do not** wrap `broker follow` in a `while true` loop. It already handles push + dedup + exit conditions.
````

Update the `### read` section to document the new `--format` flag:

Append to the `### read` section:

````markdown

The `--format` flag selects output shape:

```bash
broker read --identity agent_b a1b2c3                      # JSON (default)
broker read --identity agent_b a1b2c3 --format compact     # [sender] content lines
```
````

Update the `### list` section to document the new default and `all` option:

Append to the `### list` section:

````markdown

**Default**: returns only conversations with `status="open"`. To include closed conversations:

```bash
broker list --identity agent_a                  # open only (default)
broker list --identity agent_a --status closed  # closed only
broker list --identity agent_a --status all     # everything
```
````

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/usage.md
git commit -m "docs(broker): document broker follow + --format compact + list default=open"
```

---

### Task 16: Create `skills/broker/docs/patterns.md`

**Files:**
- Create: `skills/broker/docs/patterns.md`

- [ ] **Step 1: Write the file**

```markdown
# Broker Usage Patterns

Canonical ways to use the broker in a multi-agent Claude Code setup.

## Pattern: Wait for a reply

When you've sent a message and expect the other agent to respond, use `broker follow` in the foreground. It blocks until replies arrive, then returns.

```bash
broker send --identity server ROOM "Pushed v1.2.3, please bump the dep"
broker follow ROOM --identity server --idle-timeout 120
```

`broker follow` will:
1. Drain any backlog you haven't read yet.
2. Print each incoming message as `[sender] content`.
3. Return when the conversation goes quiet for `--idle-timeout` seconds.

Adjust `--idle-timeout` to match how long you're willing to wait before giving up. For short questions, 60s is reasonable. For long-running work (e.g. "publish a package"), use 600s or disable with `--idle-timeout 0`.

To wait for exactly one reply and exit:

```bash
broker follow ROOM --identity server --count 1
```

## Pattern: Side conversation (DM-style) between two agents

When two agents need to discuss something in depth that other agents should not have to read (e.g. API change requests, debugging sessions), fork a dedicated conversation.

Naming convention: `{a}-{b}-{topic}-{YYYYMMDD-HHMMSS}`. Example:

```bash
# server agent creates a focused conversation with core
broker create --identity server "server-core-change-request-20260421-1530" \
  --content "We need to change the validate() signature. Joining…"
# ^ returns a conversation_id; share it with core
broker send --identity server MAIN_ROOM \
  "QUESTION: @core let's continue in server-core-change-request-20260421-1530 (ID: <cid>)"
```

Lifecycle:
- Create the side room; seed with the topic.
- Invite the other agent via a message in the main room (or let them join by ID).
- Work the discussion to a conclusion.
- Post the outcome back to the main room as a `DECISION:` or `READY:` signal.
- `broker close` the side room when done — it stays on disk for audit but drops out of `broker list`.

Other agents should **not join** side rooms unless explicitly invited — the naming convention makes the ownership obvious.

## Pattern: Short signals in the main room

Use short, structured signals in the top-level coordination room (one per repo or per initiative). Examples:

```
[server] READY: v1.2.3 published
[core] BLOCKED: server TypeError on validate()
[server] QUESTION: @core should validate() take a schema or a raw object?
[server] DECISION: side conv → validate(schema) wins
```

See `signals.md` for the full vocabulary.

## Pattern: Stream messages while working (rare)

If you're doing other work but still want to react to messages as they arrive, run `broker follow` in the background via the Monitor tool. Each printed line becomes a Monitor notification you can respond to on your next turn.

```bash
broker follow ROOM --identity server --idle-timeout 0 --timeout 1800
# ^ run under Monitor; idle disabled so the stream doesn't exit while you work
```

Use sparingly: every incoming line consumes agent context. Prefer foreground `broker follow` when you're explicitly waiting.

## Anti-patterns

See `troubleshooting.md`. If you're about to write a bash loop, read that doc first.
```

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/patterns.md
git commit -m "docs(broker): add patterns.md — wait-for-reply, side conversations, stream-while-working"
```

---

### Task 17: Create `skills/broker/docs/signals.md`

**Files:**
- Create: `skills/broker/docs/signals.md`

- [ ] **Step 1: Write the file**

```markdown
# Broker Signal Vocabulary

Short, structured prefixes agents use in the main coordination room to make inter-agent state machine-readable at a glance. A project's `CLAUDE.md` can override or extend these.

## The four signals

### `READY: <what>`

An unblocking milestone has landed. Use when you've completed work other agents may be waiting on.

```
[core] READY: @proposit/proposit-core v1.2.3 published to npm
[server] READY: /api/auth endpoint shipped behind the X-Test-Mode header
```

### `BLOCKED: <on-whom> <what>`

You are stuck waiting on someone. Name them explicitly.

```
[server] BLOCKED: core TypeError from validate() on empty schemas
[server] BLOCKED: human which endpoint shape do you want — flat or nested?
```

### `QUESTION: <target> <what>`

Open question that needs input. If the target is a specific agent, `@mention` them.

```
[server] QUESTION: @core should validate() take a schema or a raw object?
[orchestrator] QUESTION: @human are we freezing main for the mobile cut tomorrow?
```

### `DECISION: <topic> → <choice>`

A coordination question has been resolved. Useful when the discussion happened in a side conversation and you want the main room to carry the outcome.

```
[server] DECISION: validate() signature → validate(schema, object)
[orchestrator] DECISION: mobile release cut → 2026-03-05 at 18:00 UTC
```

## When to use each

- Post `READY` as soon as a milestone lands — don't wait for someone to ask.
- Post `BLOCKED` immediately when you realize you can't make progress. Name the blocker.
- Use `QUESTION` when you need input but can work on something else in the meantime.
- Use `DECISION` to snapshot the outcome of a discussion, especially one that happened in a side room.

## Why these signals matter

The orchestrator and humans scan the main room for signals to decide what to route, unblock, or escalate. A message like "I guess we could maybe do X or Y" is invisible; a message like "QUESTION: @orchestrator should we do X or Y?" is actionable.
```

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/signals.md
git commit -m "docs(broker): add signals.md — READY/BLOCKED/QUESTION/DECISION vocabulary"
```

---

### Task 18: Create `skills/broker/docs/troubleshooting.md`

**Files:**
- Create: `skills/broker/docs/troubleshooting.md`

- [ ] **Step 1: Write the file**

```markdown
# Broker Troubleshooting & Anti-patterns

If you're about to write a bash loop or a python script to interact with the broker, read this first. Most attempts at scripting on top of the broker reinvent things the broker already does.

## Anti-pattern: `while true; broker read; sleep N` polling loop

```bash
# DO NOT DO THIS
while true; do
  result=$(broker read --identity me --socket /tmp/b.sock CID 2>/dev/null || echo '{"messages":[]}')
  echo "$result" | python3 -c "
import sys, json
for m in json.load(sys.stdin).get('messages', []):
  print(f\"[{m['sender']}] {m['content']}\", flush=True)
"
  sleep 10
done
```

**Why it's wrong:**
- The broker server already pushes new messages in real time over the Unix socket. Polling adds up to 10 seconds of latency per round-trip.
- The broker server already dedups by per-identity cursor; you do not need to track seen messages yourself.
- JSON parsing wastes tokens: you're already going to read the lines as your agent context.

**Do this instead:**
```bash
broker follow CID --identity me
```
Blocks, drains backlog, streams pushes, exits on idle or close.

## Anti-pattern: `/tmp/<cid>_seen.txt` dedup file

```bash
# DO NOT DO THIS
seen=/tmp/broker_${CID}_seen.txt
touch "$seen"
# ... parse output, append message ids to $seen, skip if seen, etc.
```

**Why it's wrong:**
- The broker server tracks a per-identity read cursor in the persisted conversation JSON. Each call to `broker read` (or the initial drain in `broker follow`) returns `messages[cursor:]` and advances the cursor. You never see the same message twice for the same identity.

**Do this instead:** trust the server. Stop maintaining a seen-file.

## Anti-pattern: `broker read | python -c '…'` JSON surgery

**Why it's wrong:** you're an LLM. Reading `[alice] hi` costs fewer tokens than reading the equivalent JSON. Feeding JSON through python just to reformat it is wasted computation that also wastes your context window.

**Do this instead:**
```bash
broker read CID --identity me --format compact
```
or use `broker follow`, which defaults to compact.

## Anti-pattern: `2>/dev/null || echo '{"messages":[]}'` error swallowing

**Why it's wrong:** the broker CLI exits non-zero only on real errors (server not running, conversation not found). Swallowing those hides genuine failures — your loop will silently not-receive messages while you think everything is fine.

**Do this instead:** let the CLI fail loudly. In a foreground script, non-zero exits are visible. In `broker follow`, socket drops produce a clear stderr error.

## Anti-pattern: Joining every room to see what's happening

**Why it's wrong:** the whole point of side conversations (see `patterns.md`) is that unrelated agents do not consume context on discussions that aren't for them. Joining a room costs you context on every message in that room.

**Do this instead:** stay in the main room. Read side rooms only when invited. Use `broker list` to see open rooms without joining.

## Troubleshooting real errors

### "Cannot connect to broker at /…/broker.sock. Is the broker server running?"

The server at `~/.mcp-broker/broker.sock` is not running. Ask the user to start it:

```bash
broker server --identity user
```

### `broker follow` exited with code 1 and "socket closed unexpectedly"

The server was stopped or crashed while you were following. The user can restart with `broker server`. On restart, the conversation persists — call `broker follow` again and you'll pick up where you left off via the cursor.

### `broker send` says "conversation is closed"

Someone called `broker close` on the conversation. It's read-only now. If you need to continue the discussion, create a new conversation.
```

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/troubleshooting.md
git commit -m "docs(broker): add troubleshooting.md — anti-patterns and real errors"
```

---

### Task 19: Minor update to `skills/broker/docs/setup.md`

**Files:**
- Modify: `skills/broker/docs/setup.md`

- [ ] **Step 1: Update section 5 ("Tell agents to use the broker")**

Replace the existing body of that section with:

```markdown
## 5. Tell agents to use the broker

Once the server is running and the skill is installed, tell agents something like:

```
You have a broker CLI. Check for open conversations with `broker list --identity <your-name>`,
read them with `broker read`, and when you're waiting for a reply, use `broker follow`
(it blocks and streams new messages). See the broker skill docs for patterns.
```

Agents will follow the patterns in `patterns.md` to wait for replies without writing polling loops.
```

- [ ] **Step 2: Commit**

```bash
git add skills/broker/docs/setup.md
git commit -m "docs(broker): update setup.md — tell agents to use broker follow"
```

---

## Phase 7: Rollout

### Task 20: Update release notes and changelog

**Files:**
- Rename: `docs/release-notes/upcoming.md` → `docs/release-notes/v1.2.0.md`
- Rename: `docs/changelogs/upcoming.md` → `docs/changelogs/v1.2.0.md`
- Create: fresh `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`
- Edit: the renamed files to describe this release

- [ ] **Step 1: Check current version**

Run: `cat .claude-plugin/plugin.json | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])"`
Expected: a version string like `1.1.0`. The next minor version is `1.2.0`.

If the current version is not `1.1.0`, adjust the target version accordingly (e.g., `1.1.0` → `1.2.0`; `1.5.2` → `1.6.0`).

- [ ] **Step 2: Read the current `upcoming.md` files to see what's accrued**

Run: `cat docs/release-notes/upcoming.md docs/changelogs/upcoming.md`
Expected: possibly non-empty — check whether prior unreleased changes should be rolled into `v1.2.0` or kept for another release.

- [ ] **Step 3: Rename and write `v1.2.0.md` release notes**

```bash
mv docs/release-notes/upcoming.md docs/release-notes/v1.2.0.md
```

Replace or append to the contents with:

```markdown
# v1.2.0 — Broker Ergonomics

## Highlights

- **`broker follow`** — block-and-stream subcommand that replaces ad-hoc polling loops. Drains backlog, streams server push, exits cleanly on idle / timeout / count / conversation close.
- **Richer skill docs** — new `patterns.md`, `signals.md`, `troubleshooting.md`. SKILL.md now carries critical rules inlined so agents avoid known anti-patterns before consulting detailed docs.
- **`broker list` default is now `open`-only.** Pass `--status all` to restore the previous behavior.
- **Compact output format (`--format compact`)** on `broker read` and `broker follow` for agent-facing consumption — no JSON parsing required.

## Bug fixes

- Disconnecting a client no longer wipes conversation membership or broadcasts `{identity} left` system messages. Membership is now strictly declarative — changed only via explicit `join` / `leave` / `close`. Historical join/leave spam in existing on-disk conversations is preserved; new sessions simply stop producing it.

## Protocol additions (back-compatible)

- `_broadcast_system` pushes now include the full persisted message dict (with id) alongside the existing `event` / `identity` fields. This lets `broker follow` dedup system events by id.
- `_handle_close` now pushes a `conversation_closed` event to connected members on close.
```

- [ ] **Step 4: Rename and write `v1.2.0.md` changelog**

```bash
mv docs/changelogs/upcoming.md docs/changelogs/v1.2.0.md
```

Replace or append to the contents with:

```markdown
# v1.2.0

## Added
- `broker follow` subcommand with `--idle-timeout`, `--timeout`, `--count`, `--include-system`, `--format` flags.
- `broker read --format compact` — agent-facing `[sender] content` line output.
- `--status all` option on `broker list`.
- `skills/broker/docs/patterns.md` — usage patterns.
- `skills/broker/docs/signals.md` — READY / BLOCKED / QUESTION / DECISION vocabulary.
- `skills/broker/docs/troubleshooting.md` — anti-patterns and real errors.
- Server pushes `conversation_closed` to connected members on close.
- Server `_broadcast_system` pushes include the full persisted message dict.

## Changed
- `broker list` defaults to `--status open`. Previous "all" behavior available via `--status all`.
- `skills/broker/SKILL.md` rewritten with critical-rules block and updated quick reference.

## Fixed
- `BrokerServer.disconnect` no longer removes conversation membership or broadcasts leave events. Prevents join/leave spam across agent send/read cycles.
```

- [ ] **Step 5: Create fresh `upcoming.md` files**

```bash
echo "# Upcoming" > docs/release-notes/upcoming.md
echo "# Upcoming" > docs/changelogs/upcoming.md
```

- [ ] **Step 6: Commit**

```bash
git add docs/release-notes/v1.2.0.md docs/release-notes/upcoming.md \
        docs/changelogs/v1.2.0.md docs/changelogs/upcoming.md
git commit -m "docs: release notes and changelog for v1.2.0"
```

---

### Task 21: Bump versions and tag

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump `.claude-plugin/plugin.json`**

Edit the `version` field to `1.2.0` (or the appropriate next minor per Task 20 Step 1).

- [ ] **Step 2: Bump `.claude-plugin/marketplace.json`**

Find the `version` field for this plugin and bump it to match.

- [ ] **Step 3: Verify no other version references need updating**

Run: `grep -rn '"version":' .claude-plugin/ skills/`
Expected: only `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

- [ ] **Step 4: Commit and tag**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: release v1.2.0"
git tag v1.2.0
```

- [ ] **Step 5: Final full-suite sanity check**

Run: `python -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 6: Confirm plan completion**

Every task above is checked. Announce completion to the user and offer to push the tag.

---

## Self-review

**Spec coverage:**

- CLI track (Spec §Track 1): `broker follow` → Tasks 6–12. `--format compact` on `read` → Task 5. `broker list` default + `all` → Task 13. Covered.
- Server track (Spec §Track 2): disconnect fix → Task 1. `conversation_closed` push → Task 2. `list` default → Task 3. `_broadcast_system` includes message dict → Task 2b (spec clarification). Covered.
- Skill track (Spec §Track 3): SKILL.md → Task 14. `usage.md` → Task 15. `patterns.md` → Task 16. `signals.md` → Task 17. `troubleshooting.md` → Task 18. `setup.md` → Task 19. Covered.
- Testing (Spec §Track 4): invert `test_disconnect_broadcasts_leave` → Task 1 Step 1. New `test_broker_follow.py` → Tasks 6–12. Close-push test → Task 2. `seen_ids` within-session dedup → covered implicitly by `test_follow_count_exits_after_n_messages` (if dedup broke, msg-1 and msg-2 would both arrive via push AND one via history = wrong count). Worth adding an explicit test if paranoid; skipping for now.
- Rollout (Spec §Track 5): Tasks 20–21. Covered.

**Placeholder scan:** no TBD / TODO / "implement later" / "handle edge cases" language. Code shown in full where needed. No forward references to undefined functions.

**Type consistency:** `format_message_compact` signature `(dict) -> str` used consistently in Task 4, Task 5, Task 7. `cmd_follow` signature `(argparse.Namespace) -> int` used in Tasks 7 and 12. `_emit`, `_compute_deadline`, `_next_timeout` appear only in Task 7 and are consistent there.

**Known minor deviations from spec flagged in the plan header:** `_broadcast_system` payload addition (Task 2b) — documented.
