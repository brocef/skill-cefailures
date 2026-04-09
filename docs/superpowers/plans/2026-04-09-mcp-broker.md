# MCP Message Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight MCP server that lets two Claude Code instances hold structured conversations via file-backed message passing.

**Architecture:** A `ConversationStore` class handles all conversation logic and JSON file I/O. A thin FastMCP layer wraps it as 5 MCP tools (create, send, read, list, close). A separate install script wires the broker into a project's `.claude/settings.json`.

**Tech Stack:** Python 3, `mcp` SDK (FastMCP), stdlib (`json`, `pathlib`, `secrets`, `argparse`, `datetime`)

**Spec:** `docs/superpowers/specs/2026-04-09-mcp-broker-design.md`

---

### Task 1: Add mcp dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add mcp to requirements.txt**

Add `mcp>=1.0.0` as a required dependency:

```
mcp>=1.0.0
```

Add it after the existing `html2text` line, before the optional comment block.

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: mcp and its dependencies install successfully.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add mcp SDK dependency for broker server"
```

---

### Task 2: ConversationStore — create and load

**Files:**
- Create: `scripts/mcp_broker.py`
- Create: `tests/test_mcp_broker.py`

- [ ] **Step 1: Write failing tests for create_conversation and _load**

Create `tests/test_mcp_broker.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from mcp_broker import ConversationStore


@pytest.fixture
def store(tmp_path):
    """Create a ConversationStore with a temp storage directory."""
    return ConversationStore(identity="alice", storage_dir=tmp_path)


def test_create_conversation_returns_shape(store):
    """create_conversation returns conversation_id, topic, and created_by."""
    result = store.create_conversation("Test topic")
    assert "conversation_id" in result
    assert result["topic"] == "Test topic"
    assert result["created_by"] == "alice"


def test_create_conversation_persists_file(store, tmp_path):
    """create_conversation writes a JSON file to the storage directory."""
    result = store.create_conversation("Test topic")
    path = tmp_path / f"{result['conversation_id']}.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["id"] == result["conversation_id"]
    assert data["topic"] == "Test topic"
    assert data["status"] == "open"
    assert data["createdBy"] == "alice"
    assert data["messages"] == []
    assert data["cursors"]["alice"] == 0


def test_create_conversation_creates_storage_dir():
    """create_conversation creates the storage directory if it doesn't exist."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        nested = Path(td) / "deep" / "nested"
        s = ConversationStore(identity="alice", storage_dir=nested)
        result = s.create_conversation("Topic")
        assert nested.exists()
        assert (nested / f"{result['conversation_id']}.json").exists()


def test_load_nonexistent_conversation(store):
    """Loading a nonexistent conversation raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        store._load("nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: FAIL — `mcp_broker` module not found.

- [ ] **Step 3: Implement ConversationStore skeleton with create and load**

Create `scripts/mcp_broker.py`:

```python
#!/usr/bin/env python3
"""MCP server that enables two Claude Code instances to hold structured conversations."""

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


class ConversationStore:
    """File-backed conversation storage with per-identity cursors."""

    def __init__(self, identity: str, storage_dir: Path) -> None:
        self.identity = identity
        self.storage_dir = storage_dir

    def _generate_id(self) -> str:
        """Generate a short random hex ID."""
        return secrets.token_hex(3)

    def _message_id(self) -> str:
        """Generate a message ID."""
        return f"msg-{self._generate_id()}"

    def _load(self, conversation_id: str) -> dict:
        """Load a conversation from disk."""
        path = self.storage_dir / f"{conversation_id}.json"
        if not path.exists():
            raise ValueError(f"Conversation '{conversation_id}' not found")
        return json.loads(path.read_text())

    def _save(self, conversation: dict) -> None:
        """Write a conversation to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        path = self.storage_dir / f"{conversation['id']}.json"
        path.write_text(json.dumps(conversation, indent=2))

    def create_conversation(self, topic: str) -> dict:
        """Start a new conversation."""
        conv_id = self._generate_id()
        conversation = {
            "id": conv_id,
            "topic": topic,
            "status": "open",
            "createdBy": self.identity,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "cursors": {self.identity: 0},
        }
        self._save(conversation)
        return {
            "conversation_id": conv_id,
            "topic": topic,
            "created_by": self.identity,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/mcp_broker.py tests/test_mcp_broker.py
git commit -m "Add ConversationStore with create_conversation and file persistence"
```

---

### Task 3: ConversationStore — send_message

**Files:**
- Modify: `scripts/mcp_broker.py`
- Modify: `tests/test_mcp_broker.py`

- [ ] **Step 1: Write failing tests for send_message**

Append to `tests/test_mcp_broker.py`:

```python
def test_send_message_returns_shape(store):
    """send_message returns message_id, conversation_id, and sender."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    result = store.send_message(cid, "Hello world")
    assert result["conversation_id"] == cid
    assert result["sender"] == "alice"
    assert result["message_id"].startswith("msg-")


def test_send_message_appends_to_conversation(store, tmp_path):
    """send_message appends the message to the conversation file."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    store.send_message(cid, "First message")
    store.send_message(cid, "Second message")

    data = json.loads((tmp_path / f"{cid}.json").read_text())
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "First message"
    assert data["messages"][0]["sender"] == "alice"
    assert data["messages"][1]["content"] == "Second message"
    assert "timestamp" in data["messages"][0]


def test_send_message_not_found(store):
    """send_message raises ValueError for nonexistent conversation."""
    with pytest.raises(ValueError, match="not found"):
        store.send_message("nonexistent", "Hello")


def test_send_message_closed_conversation(store):
    """send_message raises ValueError for a closed conversation."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    store.close_conversation(cid)
    with pytest.raises(ValueError, match="closed"):
        store.send_message(cid, "Should fail")
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: New tests FAIL — `send_message` and `close_conversation` not defined.

- [ ] **Step 3: Implement send_message and close_conversation**

Add to the `ConversationStore` class in `scripts/mcp_broker.py`:

```python
    def send_message(self, conversation_id: str, content: str) -> dict:
        """Append a message to a conversation."""
        conversation = self._load(conversation_id)
        if conversation["status"] == "closed":
            raise ValueError(f"Conversation '{conversation_id}' is closed")
        msg_id = self._message_id()
        message = {
            "id": msg_id,
            "sender": self.identity,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        conversation["messages"].append(message)
        # Advance sender's cursor to include their own message
        conversation["cursors"][self.identity] = len(conversation["messages"])
        self._save(conversation)
        return {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "sender": self.identity,
        }

    def close_conversation(self, conversation_id: str) -> dict:
        """Mark a conversation as closed (read-only)."""
        conversation = self._load(conversation_id)
        conversation["status"] = "closed"
        self._save(conversation)
        return {
            "conversation_id": conversation_id,
            "status": "closed",
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/mcp_broker.py tests/test_mcp_broker.py
git commit -m "Add send_message and close_conversation to ConversationStore"
```

---

### Task 4: ConversationStore — read_new_messages with cursor tracking

**Files:**
- Modify: `scripts/mcp_broker.py`
- Modify: `tests/test_mcp_broker.py`

- [ ] **Step 1: Write failing tests for read_new_messages**

Append to `tests/test_mcp_broker.py`:

```python
def test_read_new_messages_returns_unread(store, tmp_path):
    """read_new_messages returns only messages after the caller's cursor."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]

    # Simulate another identity sending messages
    bob = ConversationStore(identity="bob", storage_dir=tmp_path)
    bob.send_message(cid, "Message from bob")

    result = store.read_new_messages(cid)
    assert result["conversation_id"] == cid
    assert len(result["messages"]) == 1
    assert result["messages"][0]["sender"] == "bob"
    assert result["messages"][0]["content"] == "Message from bob"
    assert result["remaining_unread"] == 0


def test_read_new_messages_advances_cursor(store, tmp_path):
    """Reading messages advances the cursor so they aren't returned again."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]

    bob = ConversationStore(identity="bob", storage_dir=tmp_path)
    bob.send_message(cid, "First")
    bob.send_message(cid, "Second")

    # First read gets both
    result1 = store.read_new_messages(cid)
    assert len(result1["messages"]) == 2

    # Second read gets nothing
    result2 = store.read_new_messages(cid)
    assert len(result2["messages"]) == 0
    assert result2["remaining_unread"] == 0


def test_read_new_messages_empty_when_caught_up(store):
    """read_new_messages returns empty array when there's nothing new."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    result = store.read_new_messages(cid)
    assert result["messages"] == []
    assert result["remaining_unread"] == 0


def test_cursor_isolation(tmp_path):
    """Two identities have independent cursors on the same conversation."""
    alice = ConversationStore(identity="alice", storage_dir=tmp_path)
    bob = ConversationStore(identity="bob", storage_dir=tmp_path)

    created = alice.create_conversation("Topic")
    cid = created["conversation_id"]

    alice.send_message(cid, "From alice")
    bob.send_message(cid, "From bob")

    # Alice sent the first message so her cursor is at 1.
    # Bob sent the second so his cursor is at 2.
    # Alice should see bob's message (index 1).
    alice_result = alice.read_new_messages(cid)
    assert len(alice_result["messages"]) == 1
    assert alice_result["messages"][0]["sender"] == "bob"

    # Bob should see alice's message (index 0).
    bob_result = bob.read_new_messages(cid)
    assert len(bob_result["messages"]) == 1
    assert bob_result["messages"][0]["sender"] == "alice"


def test_read_new_messages_not_found(store):
    """read_new_messages raises ValueError for nonexistent conversation."""
    with pytest.raises(ValueError, match="not found"):
        store.read_new_messages("nonexistent")
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: New tests FAIL — `read_new_messages` not defined.

- [ ] **Step 3: Implement read_new_messages**

Add to the `ConversationStore` class in `scripts/mcp_broker.py`:

```python
    def read_new_messages(self, conversation_id: str) -> dict:
        """Read messages not yet seen by the calling identity."""
        conversation = self._load(conversation_id)
        cursor = conversation["cursors"].get(self.identity, 0)
        messages = conversation["messages"][cursor:]
        # Advance cursor
        conversation["cursors"][self.identity] = len(conversation["messages"])
        self._save(conversation)
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": m["id"],
                    "sender": m["sender"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                }
                for m in messages
            ],
            "remaining_unread": 0,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/mcp_broker.py tests/test_mcp_broker.py
git commit -m "Add read_new_messages with per-identity cursor tracking"
```

---

### Task 5: ConversationStore — list_conversations

**Files:**
- Modify: `scripts/mcp_broker.py`
- Modify: `tests/test_mcp_broker.py`

- [ ] **Step 1: Write failing tests for list_conversations**

Append to `tests/test_mcp_broker.py`:

```python
def test_list_conversations_all(store):
    """list_conversations returns all conversations."""
    store.create_conversation("Topic A")
    store.create_conversation("Topic B")
    result = store.list_conversations()
    assert len(result["conversations"]) == 2
    topics = {c["topic"] for c in result["conversations"]}
    assert topics == {"Topic A", "Topic B"}


def test_list_conversations_shape(store):
    """Each conversation in the list has the expected fields."""
    store.create_conversation("Topic")
    result = store.list_conversations()
    conv = result["conversations"][0]
    assert "id" in conv
    assert "topic" in conv
    assert "status" in conv
    assert "created_by" in conv
    assert "message_count" in conv
    assert "unread_count" in conv


def test_list_conversations_filter_by_status(store):
    """list_conversations filters by status when provided."""
    c1 = store.create_conversation("Open one")
    store.create_conversation("Open two")
    store.close_conversation(c1["conversation_id"])

    open_result = store.list_conversations(status="open")
    assert len(open_result["conversations"]) == 1
    assert open_result["conversations"][0]["topic"] == "Open two"

    closed_result = store.list_conversations(status="closed")
    assert len(closed_result["conversations"]) == 1
    assert closed_result["conversations"][0]["topic"] == "Open one"


def test_list_conversations_unread_count(tmp_path):
    """unread_count is relative to the calling identity's cursor."""
    alice = ConversationStore(identity="alice", storage_dir=tmp_path)
    bob = ConversationStore(identity="bob", storage_dir=tmp_path)

    created = alice.create_conversation("Topic")
    cid = created["conversation_id"]
    alice.send_message(cid, "Msg 1")
    alice.send_message(cid, "Msg 2")

    # Bob hasn't read anything — should see 2 unread
    bob_list = bob.list_conversations()
    conv = [c for c in bob_list["conversations"] if c["id"] == cid][0]
    assert conv["unread_count"] == 2
    assert conv["message_count"] == 2

    # Bob reads messages
    bob.read_new_messages(cid)
    bob_list = bob.list_conversations()
    conv = [c for c in bob_list["conversations"] if c["id"] == cid][0]
    assert conv["unread_count"] == 0


def test_list_conversations_empty(store):
    """list_conversations returns empty list when no conversations exist."""
    result = store.list_conversations()
    assert result["conversations"] == []
```

- [ ] **Step 2: Run tests to verify the new tests fail**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: New tests FAIL — `list_conversations` not defined.

- [ ] **Step 3: Implement list_conversations**

Add to the `ConversationStore` class in `scripts/mcp_broker.py`:

```python
    def list_conversations(self, status: str | None = None) -> dict:
        """List all conversations, optionally filtered by status."""
        conversations = []
        if not self.storage_dir.exists():
            return {"conversations": []}
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            if status and data["status"] != status:
                continue
            cursor = data["cursors"].get(self.identity, 0)
            conversations.append({
                "id": data["id"],
                "topic": data["topic"],
                "status": data["status"],
                "created_by": data["createdBy"],
                "message_count": len(data["messages"]),
                "unread_count": len(data["messages"]) - cursor,
            })
        return {"conversations": conversations}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/mcp_broker.py tests/test_mcp_broker.py
git commit -m "Add list_conversations with status filtering and unread counts"
```

---

### Task 6: MCP server layer and CLI entry point

**Files:**
- Modify: `scripts/mcp_broker.py`

- [ ] **Step 1: Add FastMCP tool wrappers and main() to mcp_broker.py**

Add to the bottom of `scripts/mcp_broker.py`:

```python
import argparse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-broker")

store: ConversationStore


@mcp.tool()
def create_conversation(topic: str) -> dict:
    """Start a new conversation with the given topic."""
    return store.create_conversation(topic)


@mcp.tool()
def send_message(conversation_id: str, content: str) -> dict:
    """Append a message to an existing conversation."""
    return store.send_message(conversation_id, content)


@mcp.tool()
def read_new_messages(conversation_id: str) -> dict:
    """Read messages not yet seen by the calling identity."""
    return store.read_new_messages(conversation_id)


@mcp.tool()
def list_conversations(status: str | None = None) -> dict:
    """List all conversations, optionally filtered by status ('open' or 'closed')."""
    return store.list_conversations(status)


@mcp.tool()
def close_conversation(conversation_id: str) -> dict:
    """Mark a conversation as closed. Closed conversations are read-only."""
    return store.close_conversation(conversation_id)


def main() -> None:
    """Parse CLI args and start the MCP server."""
    global store
    parser = argparse.ArgumentParser(description="MCP message broker server")
    parser.add_argument("--identity", required=True, help="Identity for this connection (e.g. 'core')")
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=Path.home() / ".mcp-broker" / "conversations",
        help="Directory for conversation files (default: ~/.mcp-broker/conversations)",
    )
    args = parser.parse_args()
    store = ConversationStore(identity=args.identity, storage_dir=args.storage_dir)
    mcp.run()


if __name__ == "__main__":
    main()
```

Move the `import argparse` to the top of the file with the other imports. Add `from mcp.server.fastmcp import FastMCP` to the imports block as well.

- [ ] **Step 2: Verify the script parses --help**

Run: `python scripts/mcp_broker.py --help`
Expected: Help text showing `--identity` and `--storage-dir` options.

- [ ] **Step 3: Commit**

```bash
git add scripts/mcp_broker.py
git commit -m "Add FastMCP tool wrappers and CLI entry point"
```

---

### Task 7: Install script

**Files:**
- Create: `scripts/install_broker.py`
- Create: `tests/test_install_broker.py`

- [ ] **Step 1: Write failing tests for install_broker**

Create `tests/test_install_broker.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import install_broker


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with a .claude/ subdirectory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return tmp_path


def test_install_writes_broker_entry(project_dir):
    """install_broker writes the mcpServers.broker entry to settings.json."""
    install_broker.install_broker(
        identity="core",
        project_dir=project_dir,
    )
    settings_path = project_dir / ".claude" / "settings.json"
    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    broker = data["mcpServers"]["broker"]
    assert broker["type"] == "stdio"
    assert "--identity" in broker["args"]
    assert "core" in broker["args"]
    assert broker["args"][0].endswith("mcp_broker.py")


def test_install_preserves_existing_keys(project_dir):
    """install_broker does not clobber other settings."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.write_text(json.dumps({
        "otherKey": "preserved",
        "mcpServers": {"other-server": {"command": "node"}},
    }))

    install_broker.install_broker(identity="core", project_dir=project_dir)

    data = json.loads(settings_path.read_text())
    assert data["otherKey"] == "preserved"
    assert "other-server" in data["mcpServers"]
    assert "broker" in data["mcpServers"]


def test_install_overwrites_existing_broker(project_dir):
    """Re-running install with a different identity updates the entry."""
    install_broker.install_broker(identity="core", project_dir=project_dir)
    install_broker.install_broker(identity="server", project_dir=project_dir)

    settings_path = project_dir / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text())
    assert "server" in data["mcpServers"]["broker"]["args"]


def test_install_with_storage_dir(project_dir):
    """--storage-dir is passed through to the broker args."""
    install_broker.install_broker(
        identity="core",
        project_dir=project_dir,
        storage_dir=Path("/custom/path"),
    )
    settings_path = project_dir / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text())
    args = data["mcpServers"]["broker"]["args"]
    assert "--storage-dir" in args
    assert "/custom/path" in args


def test_remove_broker(project_dir):
    """remove_broker removes the broker entry from settings.json."""
    install_broker.install_broker(identity="core", project_dir=project_dir)
    install_broker.remove_broker(project_dir=project_dir)

    settings_path = project_dir / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text())
    assert "broker" not in data["mcpServers"]


def test_remove_broker_no_entry(project_dir, capsys):
    """remove_broker handles missing broker entry gracefully."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings_path.write_text(json.dumps({"mcpServers": {}}))

    install_broker.remove_broker(project_dir=project_dir)
    captured = capsys.readouterr()
    assert "not configured" in captured.err


def test_no_claude_dir(tmp_path):
    """install_broker exits with error if .claude/ doesn't exist."""
    with pytest.raises(SystemExit):
        install_broker.install_broker(identity="core", project_dir=tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_install_broker.py -v`
Expected: FAIL — `install_broker` module not found.

- [ ] **Step 3: Implement install_broker.py**

Create `scripts/install_broker.py`:

```python
#!/usr/bin/env python3
"""Wire the MCP broker into a project's .claude/settings.json."""

import argparse
import json
import sys
from pathlib import Path

BROKER_SCRIPT = Path(__file__).resolve().parent / "mcp_broker.py"


def install_broker(
    identity: str,
    project_dir: Path,
    storage_dir: Path | None = None,
) -> None:
    """Add the broker MCP server entry to the project's settings.json."""
    claude_dir = project_dir / ".claude"
    if not claude_dir.is_dir():
        print(f"Error: {claude_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    settings_path = claude_dir / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    else:
        settings = {}

    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    broker_args = [str(BROKER_SCRIPT), "--identity", identity]
    if storage_dir:
        broker_args.extend(["--storage-dir", str(storage_dir)])

    settings["mcpServers"]["broker"] = {
        "command": sys.executable,
        "args": broker_args,
        "type": "stdio",
    }

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Installed broker (identity={identity}) in {settings_path}")


def remove_broker(project_dir: Path) -> None:
    """Remove the broker entry from the project's settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        print("Warning: settings.json not found", file=sys.stderr)
        return

    settings = json.loads(settings_path.read_text())
    mcp_servers = settings.get("mcpServers", {})

    if "broker" not in mcp_servers:
        print("Warning: broker is not configured in settings.json", file=sys.stderr)
        return

    del mcp_servers["broker"]
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Removed broker from {settings_path}")


def main() -> None:
    """Parse CLI args and install or remove the broker."""
    parser = argparse.ArgumentParser(
        description="Install or remove the MCP broker in a project's .claude/settings.json."
    )
    parser.add_argument("--identity", help="Identity for this connection (e.g. 'core')")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument("--storage-dir", type=Path, help="Custom storage directory for conversations")
    parser.add_argument("--remove", action="store_true", help="Remove the broker entry")

    args = parser.parse_args()

    if args.remove:
        remove_broker(project_dir=args.project_dir)
    else:
        if not args.identity:
            print("Error: --identity is required for installation", file=sys.stderr)
            sys.exit(1)
        install_broker(
            identity=args.identity,
            project_dir=args.project_dir,
            storage_dir=args.storage_dir,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_install_broker.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests across all files PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/install_broker.py tests/test_install_broker.py
git commit -m "Add install_broker script to wire broker into project settings"
```

---

### Task 8: End-to-end smoke test

**Files:**
- Modify: `tests/test_mcp_broker.py`

- [ ] **Step 1: Write an end-to-end test**

Append to `tests/test_mcp_broker.py`:

```python
def test_full_conversation_flow(tmp_path):
    """End-to-end: create, send, read, list, close."""
    alice = ConversationStore(identity="alice", storage_dir=tmp_path)
    bob = ConversationStore(identity="bob", storage_dir=tmp_path)

    # Alice creates a conversation
    created = alice.create_conversation("Design review")
    cid = created["conversation_id"]
    assert created["created_by"] == "alice"

    # Alice sends a message
    sent = alice.send_message(cid, "Please review the PR")
    assert sent["sender"] == "alice"

    # Bob reads it
    bob_read = bob.read_new_messages(cid)
    assert len(bob_read["messages"]) == 1
    assert bob_read["messages"][0]["content"] == "Please review the PR"

    # Bob replies
    bob.send_message(cid, "LGTM, merging now")

    # Alice reads the reply
    alice_read = alice.read_new_messages(cid)
    assert len(alice_read["messages"]) == 1
    assert alice_read["messages"][0]["content"] == "LGTM, merging now"

    # List shows 1 open conversation with 0 unread for both
    alice_list = alice.list_conversations()
    assert len(alice_list["conversations"]) == 1
    assert alice_list["conversations"][0]["unread_count"] == 0
    assert alice_list["conversations"][0]["message_count"] == 2

    # Close it
    closed = alice.close_conversation(cid)
    assert closed["status"] == "closed"

    # Sending to closed conversation fails
    with pytest.raises(ValueError, match="closed"):
        bob.send_message(cid, "Too late")

    # List with status filter
    open_list = alice.list_conversations(status="open")
    assert len(open_list["conversations"]) == 0
    closed_list = alice.list_conversations(status="closed")
    assert len(closed_list["conversations"]) == 1
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_mcp_broker.py
git commit -m "Add end-to-end conversation flow test"
```
