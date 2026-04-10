# Broker CLI Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the MCP server interface with CLI subcommands and a Claude Code skill so agents use `broker` via Bash instead of MCP tools.

**Architecture:** `broker_cli.py` gets argparse subcommands for one-shot operations (create, send, read, list, join, leave, close, members) plus `server` and `repl` modes. Each one-shot subcommand connects to the Unix domain socket via `BrokerClient`, performs one operation, prints JSON to stdout, and exits. A new `skills/broker/` skill teaches agents how to use the CLI. MCP-related files are deleted.

**Tech Stack:** Python 3, asyncio, argparse, pytest, Unix domain sockets

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scripts/broker_cli.py` | **Modified.** Argparse with subcommands: `server`, `repl`, `create`, `send`, `read`, `list`, `members`, `join`, `leave`, `close`. One-shot subcommands use `BrokerClient`. |
| `scripts/broker_server.py` | **Unchanged.** Socket server, state, routing, persistence. |
| `scripts/broker_client.py` | **Unchanged.** Async socket client. |
| `tests/test_broker_cli.py` | **Modified.** Add tests for one-shot subcommands. Keep existing REPL tests. |
| `skills/broker/SKILL.md` | **New.** Skill routing layer with triggers, polling pattern, quick reference. |
| `skills/broker/docs/usage.md` | **New.** Full CLI reference with examples. |
| `skills/broker/docs/setup.md` | **New.** Installation and configuration instructions. |
| `.claude-plugin/plugin.json` | **Modified.** Add `"broker"` to keywords. |
| `README.md` | **Modified.** Remove MCP references, add CLI usage. |
| `scripts/mcp_broker.py` | **Deleted.** |
| `scripts/install_broker.py` | **Deleted.** |
| `tests/test_mcp_broker.py` | **Deleted.** |
| `tests/test_install_broker.py` | **Deleted.** |

---

### Task 1: Add one-shot subcommand infrastructure to broker_cli.py

**Files:**
- Modify: `scripts/broker_cli.py:375-407`
- Test: `tests/test_broker_cli.py`

This task converts the flat `--server` / default argparse structure into subcommands and adds the `create` subcommand as the first one-shot command. We'll add the rest in subsequent tasks.

- [ ] **Step 1: Write failing test for the `create` subcommand**

Add this to `tests/test_broker_cli.py`:

```python
import asyncio
import json
import os
import tempfile

# Add these fixtures at module level, after the existing fixtures:

@pytest.fixture
def sock_path():
    """Create a short socket path to avoid macOS 104-char AF_UNIX limit."""
    fd, path = tempfile.mkstemp(prefix="brk_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def running_server(tmp_path, sock_path):
    """Start a broker server in a background task, yield (server, sock_path), then shut down."""
    from broker_server import BrokerServer, start_server

    server = BrokerServer(storage_dir=tmp_path)
    loop = asyncio.new_event_loop()
    srv = loop.run_until_complete(start_server(server, sock_path))
    yield server, sock_path, loop
    srv.close()
    loop.run_until_complete(srv.wait_closed())
    loop.close()


# ---------------------------------------------------------------------------
# One-shot subcommand tests
# ---------------------------------------------------------------------------

def test_create_subcommand(running_server):
    """'broker create' creates a conversation and prints JSON."""
    server, sock, loop = running_server
    from broker_cli import run_oneshot

    output = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test topic"})
    )
    assert "conversation_id" in output
    assert output["topic"] == "Test topic"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_cli.py::test_create_subcommand -v`
Expected: FAIL — `run_oneshot` does not exist

- [ ] **Step 3: Implement `run_oneshot` and refactor `main` to use subcommands**

Replace the `main()` function and add `run_oneshot` in `scripts/broker_cli.py`. The key changes:

1. Add `run_oneshot(sock_path, identity, request_type, params)` — connects via `BrokerClient`, sends one request, returns the response data.
2. Replace the flat argparse with subparsers: `server`, `repl`, `create`, `send`, `read`, `list`, `members`, `join`, `leave`, `close`.
3. Each one-shot subcommand calls `run_oneshot`, prints JSON to stdout, exits.

Replace everything from `async def run_client_mode` through end of file with:

```python
async def run_client_mode(identity: str, sock_path: str) -> None:
    """Connect to an existing broker server and run the REPL."""
    client = BrokerClient(identity=identity, sock_path=sock_path)
    try:
        await client.connect()
    except (ConnectionRefusedError, FileNotFoundError):
        print(json.dumps({"error": f"Cannot connect to broker at {sock_path}. Is the broker server running?"}), file=sys.stderr)
        sys.exit(1)

    print(f"Connected to broker at {sock_path}")
    loop = asyncio.get_event_loop()
    repl = ClientREPL(client, loop)
    try:
        await loop.run_in_executor(None, repl.lobby_loop)
    finally:
        await client.close()


async def run_server_mode(identity: str, storage_dir: Path, sock_path: str) -> None:
    """Start the socket server and run the REPL."""
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)
    print(f"Broker server listening on {sock_path}")

    repl = ServerREPL(server, identity)
    try:
        await asyncio.get_event_loop().run_in_executor(None, repl.lobby_loop)
    finally:
        srv.close()
        await srv.wait_closed()
        Path(sock_path).unlink(missing_ok=True)


async def run_oneshot(sock_path: str, identity: str, request_type: str, params: dict) -> dict:
    """Connect, send one request, return the response data, disconnect."""
    client = BrokerClient(identity=identity, sock_path=sock_path)
    try:
        await client.connect()
    except (ConnectionRefusedError, FileNotFoundError):
        print(json.dumps({"error": f"Cannot connect to broker at {sock_path}. Is the broker server running?"}), file=sys.stderr)
        sys.exit(1)
    try:
        msg = {"type": request_type, **params}
        response = await client._request(msg)
        return response
    finally:
        await client.close()


def _run_and_print(sock_path: str, identity: str, request_type: str, params: dict) -> None:
    """Run a one-shot request and print JSON result to stdout."""
    try:
        result = asyncio.run(run_oneshot(sock_path, identity, request_type, params))
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


DEFAULT_SOCKET = str(Path.home() / ".mcp-broker" / "broker.sock")
DEFAULT_STORAGE = Path.home() / ".mcp-broker" / "conversations"


def main() -> None:
    """Parse CLI args and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Message broker for multi-agent conversations"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- server ---
    p_server = subparsers.add_parser("server", help="Start the broker server and human REPL")
    p_server.add_argument("--identity", default="user", help="Identity for this session (default: user)")
    p_server.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_server.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE, help="Conversation storage directory")

    # --- repl ---
    p_repl = subparsers.add_parser("repl", help="Connect to a running broker as a client REPL")
    p_repl.add_argument("--identity", default="user", help="Identity for this session (default: user)")
    p_repl.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- create ---
    p_create = subparsers.add_parser("create", help="Create a conversation")
    p_create.add_argument("--identity", required=True, help="Your identity")
    p_create.add_argument("topic", help="Conversation topic")
    p_create.add_argument("--content", help="Optional seed message")
    p_create.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- send ---
    p_send = subparsers.add_parser("send", help="Send a message")
    p_send.add_argument("--identity", required=True, help="Your identity")
    p_send.add_argument("conversation_id", help="Conversation ID")
    p_send.add_argument("content", help="Message content")
    p_send.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- read ---
    p_read = subparsers.add_parser("read", help="Read new messages")
    p_read.add_argument("--identity", required=True, help="Your identity")
    p_read.add_argument("conversation_id", help="Conversation ID")
    p_read.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- list ---
    p_list = subparsers.add_parser("list", help="List conversations")
    p_list.add_argument("--identity", required=True, help="Your identity")
    p_list.add_argument("--status", choices=["open", "closed"], help="Filter by status")
    p_list.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- members ---
    p_members = subparsers.add_parser("members", help="List conversation members")
    p_members.add_argument("--identity", required=True, help="Your identity")
    p_members.add_argument("conversation_id", help="Conversation ID")
    p_members.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- join ---
    p_join = subparsers.add_parser("join", help="Join a conversation")
    p_join.add_argument("--identity", required=True, help="Your identity")
    p_join.add_argument("conversation_id", help="Conversation ID")
    p_join.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- leave ---
    p_leave = subparsers.add_parser("leave", help="Leave a conversation")
    p_leave.add_argument("--identity", required=True, help="Your identity")
    p_leave.add_argument("conversation_id", help="Conversation ID")
    p_leave.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- close ---
    p_close = subparsers.add_parser("close", help="Close a conversation")
    p_close.add_argument("--identity", required=True, help="Your identity")
    p_close.add_argument("conversation_id", help="Conversation ID")
    p_close.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)
    elif args.command == "server":
        asyncio.run(run_server_mode(args.identity, args.storage_dir, args.socket))
    elif args.command == "repl":
        asyncio.run(run_client_mode(args.identity, args.socket))
    elif args.command == "create":
        params = {"topic": args.topic}
        if args.content:
            params["content"] = args.content
        _run_and_print(args.socket, args.identity, "create_conversation", params)
    elif args.command == "send":
        _run_and_print(args.socket, args.identity, "send_message", {
            "conversation_id": args.conversation_id, "content": args.content,
        })
    elif args.command == "read":
        _run_and_print(args.socket, args.identity, "history", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "list":
        params = {}
        if args.status:
            params["status"] = args.status
        _run_and_print(args.socket, args.identity, "list_conversations", params)
    elif args.command == "members":
        _run_and_print(args.socket, args.identity, "list_members", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "join":
        _run_and_print(args.socket, args.identity, "join_conversation", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "leave":
        _run_and_print(args.socket, args.identity, "leave_conversation", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "close":
        _run_and_print(args.socket, args.identity, "close_conversation", {
            "conversation_id": args.conversation_id,
        })


if __name__ == "__main__":
    main()
```

Also add `import json` to the imports at the top of the file (it's not there yet).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_cli.py::test_create_subcommand -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_cli.py
git commit -m "feat: add subcommand infrastructure and create subcommand to broker CLI"
```

---

### Task 2: Add tests for remaining one-shot subcommands

**Files:**
- Test: `tests/test_broker_cli.py`

All subcommands use `run_oneshot` which is already implemented. This task adds test coverage for each.

- [ ] **Step 1: Write tests for send, read, list, members, join, leave, close subcommands**

Add to `tests/test_broker_cli.py` after `test_create_subcommand`:

```python
def test_send_subcommand(running_server):
    """'broker send' sends a message and prints JSON."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    # Create a conversation first
    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

    # Send a message
    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "send_message", {
            "conversation_id": cid, "content": "Hello",
        })
    )
    assert result["message_id"].startswith("msg-")
    assert result["conversation_id"] == cid
    assert result["sender"] == "agent_a"


def test_read_subcommand(running_server):
    """'broker read' returns new messages."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test", "content": "Seed"})
    )
    cid = result["conversation_id"]

    # Read as agent_b (should see seed message via history)
    result = loop.run_until_complete(
        run_oneshot(sock, "agent_b", "history", {"conversation_id": cid})
    )
    assert result["conversation_id"] == cid
    non_system = [m for m in result["messages"] if m["sender"] != "system"]
    assert len(non_system) >= 1
    assert non_system[0]["content"] == "Seed"


def test_list_subcommand(running_server):
    """'broker list' returns conversations."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Topic A"})
    )
    loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Topic B"})
    )

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "list_conversations", {})
    )
    assert len(result["conversations"]) == 2


def test_list_subcommand_status_filter(running_server):
    """'broker list --status open' filters conversations."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Open"})
    )
    cid = result["conversation_id"]
    loop.run_until_complete(
        run_oneshot(sock, "agent_a", "close_conversation", {"conversation_id": cid})
    )
    loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Still open"})
    )

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "list_conversations", {"status": "open"})
    )
    assert len(result["conversations"]) == 1
    assert result["conversations"][0]["topic"] == "Still open"


def test_members_subcommand(running_server):
    """'broker members' lists conversation members."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

    loop.run_until_complete(
        run_oneshot(sock, "agent_b", "join_conversation", {"conversation_id": cid})
    )

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "list_members", {"conversation_id": cid})
    )
    assert sorted(result["members"]) == ["agent_a", "agent_b"]


def test_join_subcommand(running_server):
    """'broker join' joins a conversation."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_b", "join_conversation", {"conversation_id": cid})
    )
    assert result["status"] == "joined"


def test_leave_subcommand(running_server):
    """'broker leave' leaves a conversation."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "leave_conversation", {"conversation_id": cid})
    )
    assert result["status"] == "left"


def test_close_subcommand(running_server):
    """'broker close' closes a conversation."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "close_conversation", {"conversation_id": cid})
    )
    assert result["status"] == "closed"


def test_oneshot_error_returns_error(running_server):
    """One-shot subcommand returns error for nonexistent conversation."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    with pytest.raises(ValueError, match="not found"):
        loop.run_until_complete(
            run_oneshot(sock, "agent_a", "send_message", {
                "conversation_id": "nonexistent", "content": "Hello",
            })
        )


def test_create_with_seed(running_server):
    """'broker create --content' sends seed message."""
    server, sock, loop = running_server

    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {
            "topic": "Seeded", "content": "Initial message",
        })
    )
    cid = result["conversation_id"]

    history = loop.run_until_complete(
        run_oneshot(sock, "agent_b", "history", {"conversation_id": cid})
    )
    non_system = [m for m in history["messages"] if m["sender"] != "system"]
    assert any(m["content"] == "Initial message" for m in non_system)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_cli.py -k "subcommand or oneshot or create_with_seed" -v`
Expected: All PASS (implementation from Task 1 handles all subcommands)

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_cli.py
git commit -m "test: add tests for all one-shot broker CLI subcommands"
```

---

### Task 3: Test CLI output format via _run_and_print

**Files:**
- Test: `tests/test_broker_cli.py`
- Modify: `scripts/broker_cli.py`

The `_run_and_print` function prints JSON to stdout and error JSON to stderr. Test the actual output format.

- [ ] **Step 1: Write tests for _run_and_print output**

Add to `tests/test_broker_cli.py`:

```python
def test_run_and_print_stdout(running_server, capsys):
    """_run_and_print prints JSON to stdout."""
    server, sock, loop = running_server

    from broker_cli import _run_and_print

    _run_and_print(sock, "agent_a", "create_conversation", {"topic": "Test"})
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "conversation_id" in data
    assert data["topic"] == "Test"


def test_run_and_print_error(running_server, capsys):
    """_run_and_print prints error JSON to stderr and exits 1 on error."""
    server, sock, loop = running_server

    from broker_cli import _run_and_print

    with pytest.raises(SystemExit) as exc_info:
        _run_and_print(sock, "agent_a", "send_message", {
            "conversation_id": "nonexistent", "content": "Hello",
        })
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    err_data = json.loads(captured.err)
    assert "error" in err_data
    assert "not found" in err_data["error"]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_cli.py::test_run_and_print_stdout tests/test_broker_cli.py::test_run_and_print_error -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_cli.py
git commit -m "test: add output format tests for broker CLI _run_and_print"
```

---

### Task 4: Fix existing REPL tests for subcommand-based argparse

**Files:**
- Modify: `tests/test_broker_cli.py`

The existing `test_help_flag` test checks for `"Interactive REPL"` in the help output, which will change now that the top-level parser description changed. Update it.

- [ ] **Step 1: Run existing tests to see what breaks**

Run: `python -m pytest tests/test_broker_cli.py -v`
Expected: `test_help_flag` likely fails due to changed help text. All other REPL tests should still pass since `ServerREPL` is unchanged.

- [ ] **Step 2: Update test_help_flag**

Replace the `test_help_flag` test:

```python
def test_help_flag() -> None:
    """Running broker_cli.py --help exits 0 and shows subcommands."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "scripts" / "broker_cli.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "server" in result.stdout
    assert "create" in result.stdout
    assert "send" in result.stdout
```

- [ ] **Step 3: Run all tests to verify everything passes**

Run: `python -m pytest tests/test_broker_cli.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_broker_cli.py
git commit -m "test: update help flag test for subcommand-based CLI"
```

---

### Task 5: Delete MCP-related files

**Files:**
- Delete: `scripts/mcp_broker.py`
- Delete: `scripts/install_broker.py`
- Delete: `tests/test_mcp_broker.py`
- Delete: `tests/test_install_broker.py`

- [ ] **Step 1: Delete the files**

```bash
git rm scripts/mcp_broker.py scripts/install_broker.py tests/test_mcp_broker.py tests/test_install_broker.py
```

- [ ] **Step 2: Run all remaining tests to verify nothing breaks**

Run: `python -m pytest tests/ -v`
Expected: All PASS — no remaining code imports from deleted files.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: delete MCP broker and install scripts, replaced by CLI subcommands"
```

---

### Task 6: Create the broker skill

**Files:**
- Create: `skills/broker/SKILL.md`
- Create: `skills/broker/docs/usage.md`
- Create: `skills/broker/docs/setup.md`

- [ ] **Step 1: Create `skills/broker/SKILL.md`**

```markdown
---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, joining multi-agent conversations, or when the user asks you to talk to another agent. Use when you see references to the broker command or conversation IDs.
---

# Broker

A chatroom-like CLI for multi-agent conversations. Multiple Claude Code agents and a human can talk to each other in real time through a shared broker server.

## Prerequisites

- The broker server must be running (`broker server` in a terminal)
- `Bash(broker:*)` must be in your allowedTools

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker list --identity NAME` | List conversations |
| `broker create --identity NAME TOPIC [--content "seed"]` | Start a conversation |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message |
| `broker read --identity NAME CONV_ID` | Read new messages |
| `broker join --identity NAME CONV_ID` | Join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker members --identity NAME CONV_ID` | List who's in a conversation |
| `broker close --identity NAME CONV_ID` | Close a conversation (read-only) |

All commands output JSON to stdout. Errors output JSON to stderr with exit code 1.

## Polling Pattern

Unless the user says otherwise, keep polling for new messages:

1. Call `broker read --identity <your-name> <conversation_id>`
2. Process any messages and respond with `broker send`
3. Repeat until the conversation is closed or you receive a stop message

Do NOT stop polling unless explicitly told to.

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference with examples and JSON output formats |
| `docs/setup.md` | Installation, configuration, and first-time setup |
```

- [ ] **Step 2: Create `skills/broker/docs/usage.md`**

```markdown
# Broker CLI Usage

## Commands

### create — Start a conversation

```bash
broker create --identity agent_a "Design a caching layer"
broker create --identity agent_a "Design a caching layer" --content "Focus on Redis for the hot path"
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "topic": "Design a caching layer",
  "created_by": "agent_a"
}
```

### send — Send a message

```bash
broker send --identity agent_a a1b2c3 "I'll start with the config module"
```

Output:
```json
{
  "message_id": "msg-d4e5f6",
  "conversation_id": "a1b2c3",
  "sender": "agent_a"
}
```

Sending auto-joins you to the conversation if you aren't a member yet.

### read — Read new messages

```bash
broker read --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "messages": [
    {"id": "msg-d4e5f6", "sender": "agent_a", "content": "I'll start with the config module", "timestamp": "2026-04-10T..."},
    {"id": "msg-g7h8i9", "sender": "system", "content": "agent_b joined", "timestamp": "2026-04-10T..."}
  ]
}
```

Messages include system messages (join/leave events) with `"sender": "system"`. Reading does not auto-join the conversation — you can read without participating.

Each call advances your cursor, so calling `read` again only returns messages since the last read.

### list — List conversations

```bash
broker list --identity agent_a
broker list --identity agent_a --status open
```

Output:
```json
{
  "conversations": [
    {
      "id": "a1b2c3",
      "topic": "Design a caching layer",
      "status": "open",
      "created_by": "agent_a",
      "message_count": 5,
      "unread_count": 2
    }
  ]
}
```

### members — List conversation members

```bash
broker members --identity agent_a a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "members": ["agent_a", "agent_b"]
}
```

### join — Join a conversation

```bash
broker join --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "joined"
}
```

### leave — Leave a conversation

```bash
broker leave --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "left"
}
```

### close — Close a conversation

```bash
broker close --identity agent_a a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "closed"
}
```

Closed conversations are read-only. No one can send messages.

## Error Handling

All errors output JSON to stderr and exit with code 1:

```json
{"error": "Conversation 'xyz' not found"}
```

```json
{"error": "Cannot connect to broker at /path/to/broker.sock. Is the broker server running?"}
```

## Common Workflow

```bash
# 1. Check for conversations
broker list --identity agent_a

# 2. Read messages from a conversation
broker read --identity agent_a a1b2c3

# 3. Respond
broker send --identity agent_a a1b2c3 "Here's my analysis..."

# 4. Poll for new messages (repeat steps 2-3)
broker read --identity agent_a a1b2c3
```
```

- [ ] **Step 3: Create `skills/broker/docs/setup.md`**

```markdown
# Broker Setup

## 1. Install the CLI

Create a symlink so `broker` is available in your `$PATH`:

```bash
ln -s /path/to/skill-cefailures/scripts/broker_cli.py /usr/local/bin/broker
```

Or add the scripts directory to your PATH:

```bash
export PATH="/path/to/skill-cefailures/scripts:$PATH"
```

If using the symlink approach, make sure the script is executable:

```bash
chmod +x /path/to/skill-cefailures/scripts/broker_cli.py
```

## 2. Start the broker server

The broker server must be running before agents can connect:

```bash
broker server
broker server --identity brian    # custom identity (default: "user")
```

This starts the Unix domain socket server at `~/.mcp-broker/broker.sock` and opens an interactive REPL. Conversations are persisted to `~/.mcp-broker/conversations/`.

To join from a separate terminal without running the server:

```bash
broker repl --identity observer
```

## 3. Configure Claude Code permissions

Add `Bash(broker:*)` to your allowedTools so agents can call the broker without permission prompts:

In your Claude Code settings or project CLAUDE.md:

```
allowedTools:
  - Bash(broker:*)
```

## 4. Install the skill

### As a plugin (recommended)

```
/plugin marketplace add brocef/skill-cefailures
/plugin install skill-cefailures
```

### Local development

```bash
claude --plugin-dir /path/to/skill-cefailures
```

## 5. Tell agents to use the broker

Once the server is running and the skill is installed, tell agents:

```
You have a broker CLI. Check for conversations with `broker list --identity <your-name>` and respond to any messages.
```

Agents will use the skill's polling pattern to keep checking for new messages.
```

- [ ] **Step 4: Verify skill structure**

```bash
ls -R skills/broker/
```

Expected:
```
skills/broker/:
SKILL.md  docs/

skills/broker/docs/:
setup.md  usage.md
```

- [ ] **Step 5: Commit**

```bash
git add skills/broker/
git commit -m "feat: add broker skill with CLI reference and setup docs"
```

---

### Task 7: Update plugin.json

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Add broker to keywords**

In `.claude-plugin/plugin.json`, change the keywords line from:

```json
"keywords": ["brain-style", "documentation-sync", "elkjs", "ieee", "knex", "permissions-auditor", "typebox"],
```

to:

```json
"keywords": ["brain-style", "broker", "documentation-sync", "elkjs", "ieee", "knex", "permissions-auditor", "typebox"],
```

- [ ] **Step 2: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: add broker to plugin keywords"
```

---

### Task 8: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README**

Read `README.md` to understand the current structure.

- [ ] **Step 2: Update the README**

Make these changes:

**Repo Structure section:** Remove `mcp_broker.py`, `install_broker.py`, `test_mcp_broker.py`, `test_install_broker.py`. Add `skills/broker/` entries. The structure should become:

```
skills/                       # Skills
  <library>/
    SKILL.md                  # Routing layer (loaded on invocation)
    docs/
      <topic>.md              # Detailed reference (read on demand)
  broker/
    SKILL.md                  # Broker skill routing layer
    docs/
      usage.md                # CLI reference
      setup.md                # Installation instructions
scripts/
  create_skill.py             # Generate skill from URL
  install_skill.py            # Symlink skills to ~/.claude/skills/
  analyze_permissions.py      # Analyze permission request logs
  log-permission-requests.sh  # Permission logging hook script
  broker_server.py            # Broker server: state, routing, persistence
  broker_client.py            # Async socket client for the broker
  broker_cli.py               # Broker CLI: server, REPL, and one-shot subcommands
tests/
  test_create_skill.py
  test_install_skill.py
  test_analyze_permissions.py
  test_broker_server.py
  test_broker_transport.py
  test_broker_client.py
  test_broker_cli.py
  test_broker_e2e.py
```

**MCP Message Broker section:** Rename to "Message Broker". Replace MCP references throughout:

- Remove "MCP" from the title and description
- Replace the architecture diagram with the CLI-based one:

```
Claude A ──Bash──► broker send/read/list ◄──┐
                                             │ Unix domain
Claude B ──Bash──► broker send/read/list ◄──┤ socket
                                             │
                    broker server        ◄───┘
                    (socket server + REPL)
```

- Replace "Install the MCP broker into agent projects" section (section 2) with:

```markdown
### 2. Install the broker CLI

Create a symlink so `broker` is available in your `$PATH`:

\`\`\`bash
ln -s /path/to/skill-cefailures/scripts/broker_cli.py /usr/local/bin/broker
chmod +x /path/to/skill-cefailures/scripts/broker_cli.py
\`\`\`

Add `Bash(broker:*)` to your Claude Code allowedTools so agents can call the broker without permission prompts.
```

- Replace the "MCP tools reference" table with a "CLI reference" table:

```markdown
### CLI reference

| Command | Description |
|---------|-------------|
| `broker create --identity NAME TOPIC [--content MSG]` | Start a new conversation, optionally with a seed message (auto-joins) |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message (auto-joins) |
| `broker read --identity NAME CONV_ID` | Read messages you haven't seen yet |
| `broker join --identity NAME CONV_ID` | Explicitly join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker list --identity NAME [--status open\|closed]` | List conversations |
| `broker members --identity NAME CONV_ID` | See who's in a conversation |
| `broker close --identity NAME CONV_ID` | Mark a conversation as read-only |
```

- Remove the install_broker.py usage sections entirely (sections about `python scripts/install_broker.py`)

- Keep the broker server startup instructions, REPL commands, and system messages sections as they are (just remove "MCP" from any references)

- [ ] **Step 3: Run a quick check**

Read the updated README to make sure it flows well and has no dangling MCP references.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README for CLI-based broker, remove MCP references"
```

---

### Task 9: Run full test suite

**Files:** None (verification only)

- [ ] **Step 1: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All PASS. No tests reference deleted files.

- [ ] **Step 2: Run a quick smoke test of the CLI**

```bash
# Verify help works
python scripts/broker_cli.py --help
python scripts/broker_cli.py create --help
python scripts/broker_cli.py send --help
```

Expected: Help output shows subcommands and their arguments.
