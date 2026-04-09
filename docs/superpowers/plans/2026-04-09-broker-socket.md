# Broker Socket Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the file-based polling broker with a Unix domain socket server for real-time message routing between Claude Code agents and a human REPL.

**Architecture:** A BrokerServer class manages in-memory conversation state, membership tracking, and message routing. It persists to disk via ConversationStore. An asyncio Unix domain socket transport connects clients. BrokerClient provides the async client interface used by both the MCP broker and the CLI REPL.

**Tech Stack:** Python 3, asyncio (stdlib), mcp SDK (FastMCP), line-delimited JSON over Unix domain socket

**Spec:** `docs/superpowers/specs/2026-04-09-broker-socket-design.md`

---

### Task 1: BrokerServer — core state management

**Files:**
- Create: `scripts/broker_server.py`
- Create: `tests/test_broker_server.py`

The BrokerServer manages all conversation state in memory. It uses a callback interface for sending messages to clients — no socket code here. This makes it testable with simple mock callbacks.

- [ ] **Step 1: Write failing tests for BrokerServer basics**

Create `tests/test_broker_server.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer


@pytest.fixture
def server(tmp_path):
    """Create a BrokerServer with a temp storage directory."""
    return BrokerServer(storage_dir=tmp_path)


def test_connect_registers_client(server):
    """connect registers a client identity with a send callback."""
    messages = []
    server.connect("alice", messages.append)
    assert "alice" in server.clients


def test_disconnect_removes_client(server):
    """disconnect removes the client."""
    server.connect("alice", lambda m: None)
    server.disconnect("alice")
    assert "alice" not in server.clients


def test_create_conversation(server):
    """create_conversation returns conversation_id, topic, created_by."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1",
        "type": "create_conversation",
        "topic": "Test topic",
    })
    assert result["type"] == "response"
    assert result["id"] == "req-1"
    assert "conversation_id" in result["data"]
    assert result["data"]["topic"] == "Test topic"
    assert result["data"]["created_by"] == "alice"


def test_create_conversation_with_seed(server):
    """create_conversation with content adds a seed message."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1",
        "type": "create_conversation",
        "topic": "Test",
        "content": "Seed message",
    })
    cid = result["data"]["conversation_id"]
    assert len(server.conversations[cid]["messages"]) == 1
    assert server.conversations[cid]["messages"][0]["content"] == "Seed message"


def test_list_conversations(server):
    """list_conversations returns all conversations."""
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "A",
    })
    server.handle_request("alice", {
        "id": "req-2", "type": "create_conversation", "topic": "B",
    })
    result = server.handle_request("alice", {
        "id": "req-3", "type": "list_conversations",
    })
    assert len(result["data"]["conversations"]) == 2


def test_error_on_unknown_type(server):
    """Unknown request type returns an error."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "bogus",
    })
    assert result["type"] == "error"
    assert result["id"] == "req-1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_server.py -v`
Expected: FAIL — `broker_server` module not found.

- [ ] **Step 3: Implement BrokerServer skeleton**

Create `scripts/broker_server.py`:

```python
#!/usr/bin/env python3
"""Broker server: in-memory conversation state, membership tracking, message routing."""

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class BrokerServer:
    """Central broker that manages conversations, membership, and message routing."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.conversations: dict[str, dict] = {}
        self.members: dict[str, set[str]] = {}  # conversation_id -> set of identities
        self.clients: dict[str, Callable] = {}  # identity -> send callback
        self._load_from_disk()

    def _generate_id(self) -> str:
        """Generate a short random hex ID."""
        return secrets.token_hex(3)

    def _message_id(self) -> str:
        """Generate a message ID."""
        return f"msg-{self._generate_id()}"

    def _timestamp(self) -> str:
        """Generate an ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _load_from_disk(self) -> None:
        """Load existing conversations from disk into memory."""
        if not self.storage_dir.exists():
            return
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            self.conversations[data["id"]] = data
            self.members.setdefault(data["id"], set())

    def _save_conversation(self, conversation_id: str) -> None:
        """Persist a single conversation to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        conv = self.conversations[conversation_id]
        path = self.storage_dir / f"{conversation_id}.json"
        path.write_text(json.dumps(conv, indent=2))

    def connect(self, identity: str, send: Callable) -> None:
        """Register a client connection."""
        self.clients[identity] = send

    def disconnect(self, identity: str) -> None:
        """Remove a client and broadcast leave events."""
        self.clients.pop(identity, None)
        for cid, member_set in list(self.members.items()):
            if identity in member_set:
                member_set.discard(identity)
                self._broadcast_system(cid, "leave", identity)

    def handle_request(self, identity: str, msg: dict) -> dict:
        """Dispatch a client request and return a response or error."""
        req_id = msg.get("id", "")
        msg_type = msg.get("type", "")

        try:
            handler = {
                "create_conversation": self._handle_create,
                "join_conversation": self._handle_join,
                "leave_conversation": self._handle_leave,
                "send_message": self._handle_send,
                "history": self._handle_history,
                "list_conversations": self._handle_list,
                "list_members": self._handle_list_members,
                "close_conversation": self._handle_close,
            }.get(msg_type)

            if not handler:
                return {"type": "error", "id": req_id, "message": f"Unknown request type: {msg_type}"}

            data = handler(identity, msg)
            return {"type": "response", "id": req_id, "data": data}
        except ValueError as e:
            return {"type": "error", "id": req_id, "message": str(e)}

    def _join_member(self, conversation_id: str, identity: str) -> None:
        """Add an identity to a conversation's member set and broadcast join."""
        members = self.members.setdefault(conversation_id, set())
        if identity not in members:
            members.add(identity)
            self._broadcast_system(conversation_id, "join", identity)

    def _broadcast_system(self, conversation_id: str, event: str, identity: str) -> None:
        """Create a system message and broadcast to conversation members."""
        msg = {
            "id": self._message_id(),
            "sender": "system",
            "content": f"{identity} {event}ed" if event == "join" else f"{identity} left",
            "timestamp": self._timestamp(),
        }
        self.conversations[conversation_id]["messages"].append(msg)
        self._save_conversation(conversation_id)
        push = {"type": "system", "conversation_id": conversation_id, "event": event, "identity": identity}
        for member in self.members.get(conversation_id, set()):
            if member != identity and member in self.clients:
                self.clients[member](push)

    def _handle_create(self, identity: str, msg: dict) -> dict:
        """Handle create_conversation request."""
        conv_id = self._generate_id()
        conversation = {
            "id": conv_id,
            "topic": msg["topic"],
            "status": "open",
            "createdBy": identity,
            "createdAt": self._timestamp(),
            "messages": [],
            "cursors": {},
        }
        self.conversations[conv_id] = conversation
        self.members[conv_id] = set()
        self._join_member(conv_id, identity)

        if msg.get("content"):
            user_msg = {
                "id": self._message_id(),
                "sender": identity,
                "content": msg["content"],
                "timestamp": self._timestamp(),
            }
            conversation["messages"].append(user_msg)

        self._save_conversation(conv_id)
        return {"conversation_id": conv_id, "topic": msg["topic"], "created_by": identity}

    def _handle_join(self, identity: str, msg: dict) -> dict:
        """Handle join_conversation request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        self._join_member(cid, identity)
        return {"conversation_id": cid, "status": "joined"}

    def _handle_leave(self, identity: str, msg: dict) -> dict:
        """Handle leave_conversation request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        members = self.members.get(cid, set())
        if identity in members:
            members.discard(identity)
            self._broadcast_system(cid, "leave", identity)
        return {"conversation_id": cid, "status": "left"}

    def _handle_send(self, identity: str, msg: dict) -> dict:
        """Handle send_message request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        conv = self.conversations[cid]
        if conv["status"] == "closed":
            raise ValueError(f"Conversation '{cid}' is closed")

        self._join_member(cid, identity)

        user_msg = {
            "id": self._message_id(),
            "sender": identity,
            "content": msg["content"],
            "timestamp": self._timestamp(),
        }
        conv["messages"].append(user_msg)
        self._save_conversation(cid)

        push = {"type": "message", "conversation_id": cid, "message": user_msg}
        for member in self.members.get(cid, set()):
            if member != identity and member in self.clients:
                self.clients[member](push)

        return {"message_id": user_msg["id"], "conversation_id": cid, "sender": identity}

    def _handle_history(self, identity: str, msg: dict) -> dict:
        """Handle history request — returns all messages for catch-up."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        conv = self.conversations[cid]
        cursor = conv["cursors"].get(identity, 0)
        messages = conv["messages"][cursor:]
        conv["cursors"][identity] = len(conv["messages"])
        self._save_conversation(cid)
        return {
            "conversation_id": cid,
            "messages": [
                {"id": m["id"], "sender": m["sender"], "content": m["content"], "timestamp": m["timestamp"]}
                for m in messages
            ],
        }

    def _handle_list(self, identity: str, msg: dict) -> dict:
        """Handle list_conversations request."""
        status_filter = msg.get("status")
        conversations = []
        for conv in self.conversations.values():
            if status_filter and conv["status"] != status_filter:
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

    def _handle_list_members(self, identity: str, msg: dict) -> dict:
        """Handle list_members request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        members = sorted(self.members.get(cid, set()))
        return {"conversation_id": cid, "members": members}

    def _handle_close(self, identity: str, msg: dict) -> dict:
        """Handle close_conversation request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        self.conversations[cid]["status"] = "closed"
        self._save_conversation(cid)
        return {"conversation_id": cid, "status": "closed"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_server.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_server.py
git commit -m "Add BrokerServer with core state management and request handling"
```

---

### Task 2: BrokerServer — membership, routing, and system messages

**Files:**
- Modify: `tests/test_broker_server.py`
- (No changes to `scripts/broker_server.py` needed — the implementation from Task 1 already includes these features. This task adds thorough tests.)

- [ ] **Step 1: Write tests for membership and message routing**

Append to `tests/test_broker_server.py`:

```python
def test_create_auto_joins(server):
    """create_conversation auto-joins the creator."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    assert "alice" in server.members[cid]


def test_send_auto_joins(server):
    """send_message auto-joins the sender."""
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("bob", {
        "id": "req-2", "type": "send_message", "conversation_id": cid, "content": "Hi",
    })
    assert "bob" in server.members[cid]


def test_send_message_pushes_to_members(server):
    """send_message pushes to other connected members."""
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
        "id": "req-3", "type": "send_message", "conversation_id": cid, "content": "Hello",
    })

    # Bob should have received the pushed message (plus system messages for joins)
    pushed = [m for m in bob_msgs if m["type"] == "message"]
    assert len(pushed) == 1
    assert pushed[0]["message"]["content"] == "Hello"
    assert pushed[0]["message"]["sender"] == "alice"


def test_send_not_pushed_to_non_members(server):
    """send_message does not push to clients not in the conversation."""
    bob_msgs = []
    server.connect("alice", lambda m: None)
    server.connect("bob", bob_msgs.append)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    # Bob does NOT join

    server.handle_request("alice", {
        "id": "req-2", "type": "send_message", "conversation_id": cid, "content": "Hello",
    })

    pushed = [m for m in bob_msgs if m["type"] == "message"]
    assert len(pushed) == 0


def test_send_not_pushed_to_sender(server):
    """send_message does not echo back to the sender."""
    alice_msgs = []
    server.connect("alice", alice_msgs.append)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]

    server.handle_request("alice", {
        "id": "req-2", "type": "send_message", "conversation_id": cid, "content": "Hello",
    })

    pushed = [m for m in alice_msgs if m["type"] == "message"]
    assert len(pushed) == 0
```

- [ ] **Step 2: Write tests for system messages**

Append to `tests/test_broker_server.py`:

```python
def test_join_broadcasts_system_message(server):
    """Joining a conversation broadcasts a system message to members."""
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

    system_msgs = [m for m in alice_msgs if m["type"] == "system"]
    assert any(m["event"] == "join" and m["identity"] == "bob" for m in system_msgs)


def test_leave_broadcasts_system_message(server):
    """Leaving a conversation broadcasts a system message to remaining members."""
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

    server.handle_request("bob", {
        "id": "req-3", "type": "leave_conversation", "conversation_id": cid,
    })

    system_msgs = [m for m in alice_msgs if m["type"] == "system" and m["event"] == "leave"]
    assert any(m["identity"] == "bob" for m in system_msgs)


def test_disconnect_broadcasts_leave(server):
    """Disconnecting broadcasts leave to all conversations the client was in."""
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
    assert any(m["identity"] == "bob" for m in system_msgs)
    assert "bob" not in server.members[cid]


def test_system_messages_not_counted_in_message_count(server):
    """System messages are excluded from message_count in list_conversations."""
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    # Bob joins — creates a system message
    server.handle_request("bob", {
        "id": "req-2", "type": "join_conversation", "conversation_id": cid,
    })
    # Alice sends a real message
    server.handle_request("alice", {
        "id": "req-3", "type": "send_message", "conversation_id": cid, "content": "Hello",
    })

    result = server.handle_request("alice", {
        "id": "req-4", "type": "list_conversations",
    })
    conv = result["data"]["conversations"][0]
    # Should count only the seed-less create + 1 real message, not system messages
    # alice auto-joined (system msg), bob joined (system msg), alice sent "Hello" (real msg)
    assert conv["message_count"] == 1
```

- [ ] **Step 3: Write tests for leave, close, history, list_members**

Append to `tests/test_broker_server.py`:

```python
def test_leave_conversation(server):
    """leave_conversation removes the client from membership."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("alice", {
        "id": "req-2", "type": "leave_conversation", "conversation_id": cid,
    })
    assert "alice" not in server.members[cid]


def test_close_conversation(server):
    """close_conversation marks conversation as closed."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("alice", {
        "id": "req-2", "type": "close_conversation", "conversation_id": cid,
    })
    assert server.conversations[cid]["status"] == "closed"


def test_send_to_closed_fails(server):
    """send_message to a closed conversation returns an error."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("alice", {
        "id": "req-2", "type": "close_conversation", "conversation_id": cid,
    })
    result = server.handle_request("alice", {
        "id": "req-3", "type": "send_message", "conversation_id": cid, "content": "Hi",
    })
    assert result["type"] == "error"
    assert "closed" in result["message"]


def test_history_returns_messages(server):
    """history returns all messages since cursor."""
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("alice", {
        "id": "req-2", "type": "send_message", "conversation_id": cid, "content": "Msg 1",
    })

    result = server.handle_request("alice", {
        "id": "req-3", "type": "history", "conversation_id": cid,
    })
    # Should include system message (alice joined) + user message
    assert len(result["data"]["messages"]) >= 1
    contents = [m["content"] for m in result["data"]["messages"]]
    assert "Msg 1" in contents


def test_list_members(server):
    """list_members returns current members of a conversation."""
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)

    result = server.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "T",
    })
    cid = result["data"]["conversation_id"]
    server.handle_request("bob", {
        "id": "req-2", "type": "join_conversation", "conversation_id": cid,
    })

    result = server.handle_request("alice", {
        "id": "req-3", "type": "list_members", "conversation_id": cid,
    })
    assert sorted(result["data"]["members"]) == ["alice", "bob"]


def test_not_found_errors(server):
    """Operations on nonexistent conversations return errors."""
    server.connect("alice", lambda m: None)
    for req_type in ["join_conversation", "leave_conversation", "send_message", "close_conversation", "history", "list_members"]:
        msg = {"id": "req-1", "type": req_type, "conversation_id": "nope"}
        if req_type == "send_message":
            msg["content"] = "Hi"
        result = server.handle_request("alice", msg)
        assert result["type"] == "error", f"{req_type} should return error"
        assert "not found" in result["message"]
```

- [ ] **Step 4: Write test for persistence**

Append to `tests/test_broker_server.py`:

```python
def test_persistence_survives_restart(tmp_path):
    """Conversations persist to disk and are loaded on restart."""
    server1 = BrokerServer(storage_dir=tmp_path)
    server1.connect("alice", lambda m: None)
    result = server1.handle_request("alice", {
        "id": "req-1", "type": "create_conversation", "topic": "Persisted",
    })
    cid = result["data"]["conversation_id"]
    server1.handle_request("alice", {
        "id": "req-2", "type": "send_message", "conversation_id": cid, "content": "Hello",
    })

    # Create a new server instance (simulates restart)
    server2 = BrokerServer(storage_dir=tmp_path)
    assert cid in server2.conversations
    assert server2.conversations[cid]["topic"] == "Persisted"
    non_system = [m for m in server2.conversations[cid]["messages"] if m["sender"] != "system"]
    assert len(non_system) >= 1
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_broker_server.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_broker_server.py
git commit -m "Add comprehensive tests for BrokerServer membership, routing, and system messages"
```

---

### Task 3: Socket transport layer

**Files:**
- Modify: `scripts/broker_server.py`
- Create: `tests/test_broker_transport.py`

Add asyncio Unix domain socket transport that wraps BrokerServer. The transport handles line-delimited JSON framing and dispatches to BrokerServer.

- [ ] **Step 1: Write integration test for socket transport**

Create `tests/test_broker_transport.py`:

```python
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path


async def _connect_client(sock_path: str) -> tuple:
    """Connect a client to the socket and return (reader, writer)."""
    reader, writer = await asyncio.open_unix_connection(sock_path)
    return reader, writer


async def _send(writer: asyncio.StreamWriter, msg: dict) -> None:
    """Send a line-delimited JSON message."""
    writer.write(json.dumps(msg).encode() + b"\n")
    await writer.drain()


async def _recv(reader: asyncio.StreamReader) -> dict:
    """Read one line-delimited JSON message."""
    line = await asyncio.wait_for(reader.readline(), timeout=2.0)
    return json.loads(line)


@pytest.mark.asyncio
async def test_socket_connect_and_create(storage_dir, tmp_path):
    """Client can connect via socket and create a conversation."""
    sock_path = str(tmp_path / "test.sock")
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        reader, writer = await _connect_client(sock_path)

        await _send(writer, {"id": "r1", "type": "connect", "identity": "alice"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r1"

        await _send(writer, {"id": "r2", "type": "create_conversation", "topic": "Test"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r2"
        assert "conversation_id" in resp["data"]

        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_message_push(storage_dir, tmp_path):
    """Messages are pushed to other connected members via socket."""
    sock_path = str(tmp_path / "test.sock")
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        r1, w1 = await _connect_client(sock_path)
        r2, w2 = await _connect_client(sock_path)

        await _send(w1, {"id": "r1", "type": "connect", "identity": "alice"})
        await _recv(r1)
        await _send(w2, {"id": "r2", "type": "connect", "identity": "bob"})
        await _recv(r2)

        await _send(w1, {"id": "r3", "type": "create_conversation", "topic": "Test"})
        resp = await _recv(r1)
        cid = resp["data"]["conversation_id"]

        await _send(w2, {"id": "r4", "type": "join_conversation", "conversation_id": cid})
        await _recv(r2)  # join response
        # alice gets bob's join system message
        sys_msg = await _recv(r1)
        assert sys_msg["type"] == "system"

        await _send(w1, {"id": "r5", "type": "send_message", "conversation_id": cid, "content": "Hello bob"})
        await _recv(r1)  # send response

        # Bob should receive the pushed message
        pushed = await _recv(r2)
        assert pushed["type"] == "message"
        assert pushed["message"]["content"] == "Hello bob"

        w1.close()
        w2.close()
        await w1.wait_closed()
        await w2.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_transport.py -v`
Expected: FAIL — `start_server` not importable.

- [ ] **Step 3: Implement socket transport in broker_server.py**

Add to the bottom of `scripts/broker_server.py`:

```python
import asyncio


async def _handle_client(server: BrokerServer, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Handle a single client connection."""
    identity = None
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            msg = json.loads(line.decode())

            if msg["type"] == "connect":
                identity = msg["identity"]
                def send(m, w=writer):
                    w.write(json.dumps(m).encode() + b"\n")
                server.connect(identity, send)
                response = {"type": "response", "id": msg.get("id", ""), "data": {"status": "connected"}}
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
            else:
                response = server.handle_request(identity, msg)
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        if identity:
            server.disconnect(identity)
        writer.close()


async def start_server(server: BrokerServer, sock_path: str) -> asyncio.AbstractServer:
    """Start the Unix domain socket server."""
    Path(sock_path).unlink(missing_ok=True)
    srv = await asyncio.start_unix_server(
        lambda r, w: _handle_client(server, r, w),
        path=sock_path,
    )
    return srv
```

Also add `import asyncio` to the top of the file if not already there.

- [ ] **Step 4: Install pytest-asyncio**

Run: `pip install pytest-asyncio`

Add `pytest-asyncio` to `requirements.txt` under a test dependencies comment if desired, or leave as a dev dependency.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_transport.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/test_install_plugin.py`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_transport.py
git commit -m "Add asyncio Unix domain socket transport for BrokerServer"
```

---

### Task 4: BrokerClient

**Files:**
- Create: `scripts/broker_client.py`
- Create: `tests/test_broker_client.py`

BrokerClient connects to the socket server, sends requests with correlation IDs, and receives push messages.

- [ ] **Step 1: Write tests for BrokerClient**

Create `tests/test_broker_client.py`:

```python
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.mark.asyncio
async def test_client_connect_and_create(tmp_path):
    """BrokerClient can connect and create a conversation."""
    sock_path = str(tmp_path / "test.sock")
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path)
        await client.connect()

        result = await client.create_conversation("Test topic")
        assert "conversation_id" in result
        assert result["topic"] == "Test topic"

        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_send_and_receive(tmp_path):
    """Two BrokerClients can send and receive messages."""
    sock_path = str(tmp_path / "test.sock")
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        result = await alice.create_conversation("Test")
        cid = result["conversation_id"]
        await bob.join_conversation(cid)

        await alice.send_message(cid, "Hello bob")

        # Give a moment for the push to arrive
        await asyncio.sleep(0.05)

        # Bob should have the message in his buffer
        messages = bob.get_new_messages(cid)
        assert len(messages) >= 1
        content_msgs = [m for m in messages if m.get("message", {}).get("sender") != "system"]
        assert any(m["message"]["content"] == "Hello bob" for m in content_msgs if "message" in m)

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_list_conversations(tmp_path):
    """BrokerClient can list conversations."""
    sock_path = str(tmp_path / "test.sock")
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path)
        await client.connect()
        await client.create_conversation("Topic A")
        await client.create_conversation("Topic B")

        result = await client.list_conversations()
        assert len(result["conversations"]) == 2

        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_list_members(tmp_path):
    """BrokerClient can list conversation members."""
    sock_path = str(tmp_path / "test.sock")
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        result = await alice.create_conversation("Test")
        cid = result["conversation_id"]
        await bob.join_conversation(cid)

        members = await alice.list_members(cid)
        assert sorted(members["members"]) == ["alice", "bob"]

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_client.py -v`
Expected: FAIL — `broker_client` module not found.

- [ ] **Step 3: Implement BrokerClient**

Create `scripts/broker_client.py`:

```python
#!/usr/bin/env python3
"""Async client for the broker socket server."""

import asyncio
import json
import secrets
from pathlib import Path


class BrokerClient:
    """Connects to the broker socket server and provides an async API."""

    def __init__(self, identity: str, sock_path: str) -> None:
        self.identity = identity
        self.sock_path = sock_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._push_buffer: dict[str, list[dict]] = {}  # conversation_id -> list of push messages
        self._listener_task: asyncio.Task | None = None
        self.on_push: asyncio.Queue[dict] | None = None  # optional queue for real-time push notifications

    async def connect(self) -> None:
        """Connect to the broker socket server."""
        self._reader, self._writer = await asyncio.open_unix_connection(self.sock_path)
        self._listener_task = asyncio.create_task(self._listen())
        await self._request({"type": "connect", "identity": self.identity})

    async def close(self) -> None:
        """Close the connection."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def _request(self, msg: dict) -> dict:
        """Send a request and wait for the correlated response."""
        req_id = f"req-{secrets.token_hex(3)}"
        msg["id"] = req_id
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        self._writer.write(json.dumps(msg).encode() + b"\n")
        await self._writer.drain()
        result = await asyncio.wait_for(future, timeout=5.0)
        if result["type"] == "error":
            raise ValueError(result["message"])
        return result.get("data", {})

    async def _listen(self) -> None:
        """Background task that reads messages from the server."""
        try:
            while True:
                line = await self._reader.readline()
                if not line:
                    break
                msg = json.loads(line.decode())
                if msg["type"] in ("response", "error") and "id" in msg:
                    future = self._pending.pop(msg["id"], None)
                    if future and not future.done():
                        future.set_result(msg)
                else:
                    # Push message (message or system event)
                    cid = msg.get("conversation_id", "")
                    self._push_buffer.setdefault(cid, []).append(msg)
                    if self.on_push:
                        await self.on_push.put(msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    def get_new_messages(self, conversation_id: str) -> list[dict]:
        """Return and clear buffered push messages for a conversation."""
        return self._push_buffer.pop(conversation_id, [])

    async def create_conversation(self, topic: str, content: str | None = None) -> dict:
        """Create a new conversation."""
        msg = {"type": "create_conversation", "topic": topic}
        if content:
            msg["content"] = content
        return await self._request(msg)

    async def send_message(self, conversation_id: str, content: str) -> dict:
        """Send a message to a conversation."""
        return await self._request({
            "type": "send_message", "conversation_id": conversation_id, "content": content,
        })

    async def join_conversation(self, conversation_id: str) -> dict:
        """Join a conversation."""
        return await self._request({
            "type": "join_conversation", "conversation_id": conversation_id,
        })

    async def leave_conversation(self, conversation_id: str) -> dict:
        """Leave a conversation."""
        return await self._request({
            "type": "leave_conversation", "conversation_id": conversation_id,
        })

    async def history(self, conversation_id: str) -> dict:
        """Get conversation history (catch-up after reconnect)."""
        return await self._request({
            "type": "history", "conversation_id": conversation_id,
        })

    async def list_conversations(self, status: str | None = None) -> dict:
        """List all conversations."""
        msg = {"type": "list_conversations"}
        if status:
            msg["status"] = status
        return await self._request(msg)

    async def list_members(self, conversation_id: str) -> dict:
        """List members of a conversation."""
        return await self._request({
            "type": "list_members", "conversation_id": conversation_id,
        })

    async def close_conversation(self, conversation_id: str) -> dict:
        """Close a conversation."""
        return await self._request({
            "type": "close_conversation", "conversation_id": conversation_id,
        })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_client.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_client.py tests/test_broker_client.py
git commit -m "Add BrokerClient async socket client with correlation ID matching"
```

---

### Task 5: Update MCP broker to use socket client

**Files:**
- Modify: `scripts/mcp_broker.py`
- Modify: `tests/test_mcp_broker.py`

Replace the direct ConversationStore usage in MCP tool handlers with BrokerClient. ConversationStore stays in the file for the server's persistence layer.

- [ ] **Step 1: Update mcp_broker.py**

Rewrite the MCP tool section of `scripts/mcp_broker.py`. Keep the `ConversationStore` class (used by `broker_server.py`). Replace the tool handlers:

```python
import asyncio
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Keep ConversationStore class as-is above this line (used by broker_server.py)

sys.path.insert(0, str(Path(__file__).parent))
from broker_client import BrokerClient

mcp = FastMCP("mcp-broker")

client: BrokerClient
loop: asyncio.AbstractEventLoop


def _run(coro):
    """Run an async coroutine from sync MCP tool handlers."""
    return loop.run_until_complete(coro)


@mcp.tool()
def create_conversation(topic: str, content: str | None = None) -> dict:
    """Start a new conversation with the given topic, optionally with a seed message."""
    return _run(client.create_conversation(topic, content))


@mcp.tool()
def send_message(conversation_id: str, content: str) -> dict:
    """Append a message to an existing conversation (auto-joins)."""
    return _run(client.send_message(conversation_id, content))


@mcp.tool()
def read_new_messages(conversation_id: str) -> dict:
    """Read messages you haven't seen yet."""
    return _run(client.history(conversation_id))


@mcp.tool()
def list_conversations(status: str | None = None) -> dict:
    """List all conversations, optionally filtered by status ('open' or 'closed')."""
    return _run(client.list_conversations(status))


@mcp.tool()
def list_members(conversation_id: str) -> dict:
    """List current members of a conversation."""
    return _run(client.list_members(conversation_id))


@mcp.tool()
def join_conversation(conversation_id: str) -> dict:
    """Explicitly join a conversation."""
    return _run(client.join_conversation(conversation_id))


@mcp.tool()
def leave_conversation(conversation_id: str) -> dict:
    """Leave a conversation."""
    return _run(client.leave_conversation(conversation_id))


@mcp.tool()
def close_conversation(conversation_id: str) -> dict:
    """Mark a conversation as read-only."""
    return _run(client.close_conversation(conversation_id))


def main() -> None:
    """Parse CLI args and start the MCP server."""
    global client, loop
    import argparse

    parser = argparse.ArgumentParser(description="MCP message broker server")
    parser.add_argument("--identity", required=True, help="Identity for this connection (e.g. 'agent_a')")
    parser.add_argument(
        "--socket",
        default=str(Path.home() / ".mcp-broker" / "broker.sock"),
        help="Path to broker socket (default: ~/.mcp-broker/broker.sock)",
    )
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    client = BrokerClient(identity=args.identity, sock_path=args.socket)
    try:
        loop.run_until_complete(client.connect())
    except (ConnectionRefusedError, FileNotFoundError):
        print(f"Error: Cannot connect to broker at {args.socket}. Is the broker server running?", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify --help works**

Run: `python scripts/mcp_broker.py --help`
Expected: Shows `--identity` and `--socket` options.

- [ ] **Step 3: Update tests**

Update `tests/test_mcp_broker.py` — keep the ConversationStore tests (they validate the server's persistence layer). The existing tests should still pass since ConversationStore is unchanged.

Run: `python -m pytest tests/test_mcp_broker.py -v`
Expected: All existing ConversationStore tests PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/mcp_broker.py tests/test_mcp_broker.py
git commit -m "Update MCP broker to use socket client instead of direct file I/O"
```

---

### Task 6: Update install_broker.py for socket path

**Files:**
- Modify: `scripts/install_broker.py`
- Modify: `tests/test_install_broker.py`

Update the install script to use `--socket` instead of `--storage-dir` in the generated .mcp.json entry.

- [ ] **Step 1: Update install_broker.py**

Change the `broker_args` construction in `install_broker`:

```python
def install_broker(
    identity: str,
    project_dir: Path,
    socket_path: Path | None = None,
) -> None:
    """Add the broker MCP server entry to the project's .mcp.json."""
    if not project_dir.is_dir():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    mcp_path = project_dir / ".mcp.json"
    if mcp_path.exists():
        config = json.loads(mcp_path.read_text())
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    broker_args = [str(BROKER_SCRIPT), "--identity", identity]
    if socket_path:
        broker_args.extend(["--socket", str(socket_path)])

    config["mcpServers"]["broker"] = {
        "command": sys.executable,
        "args": broker_args,
        "type": "stdio",
    }

    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Installed broker (identity={identity}) in {mcp_path}")
```

Update `main()` to use `--socket` instead of `--storage-dir`:

```python
    parser.add_argument("--socket", type=Path, help="Custom socket path for the broker")
```

And pass `socket_path=args.socket` to `install_broker`.

- [ ] **Step 2: Update tests**

Update `tests/test_install_broker.py`: rename `test_install_with_storage_dir` to `test_install_with_socket_path` and check for `--socket` in args instead of `--storage-dir`.

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_install_broker.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/install_broker.py tests/test_install_broker.py
git commit -m "Update install_broker to use --socket instead of --storage-dir"
```

---

### Task 7: Update broker_cli.py — server mode

**Files:**
- Modify: `scripts/broker_cli.py`
- Modify: `tests/test_broker_cli.py`

Add `--server` flag that starts the socket server alongside the REPL. The server's REPL acts as a direct participant (using BrokerServer methods, not going through the socket).

- [ ] **Step 1: Rewrite broker_cli.py with server mode**

Rewrite `scripts/broker_cli.py`:

```python
#!/usr/bin/env python3
"""Interactive REPL CLI for the MCP message broker."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


def format_conversation_line(conv: dict) -> str:
    """Format a conversation dict for display in the lobby list."""
    return (
        f'  [{conv["id"]}] "{conv["topic"]}" '
        f'({conv["status"]}, {conv["message_count"]} msgs, {conv["unread_count"]} unread)'
    )


def format_message(msg: dict) -> str:
    """Format a message dict for display."""
    return f'  [{msg["sender"]}] {msg["content"]}'


LOBBY_HELP = """\
Commands:
  list             List all conversations
  create <topic>   Create a new conversation
  join <id>        Enter a conversation
  help             Show this help
  exit             Quit"""

CONVERSATION_HELP = """\
Commands:
  read     Show new messages
  members  Show who's in this conversation
  leave    Leave the conversation and return to lobby
  close    Close the conversation (read-only for everyone)
  back     Return to lobby (stay in conversation)
  help     Show this help
  <text>   Send a message"""


class ServerREPL:
    """REPL that runs inside the server process, using BrokerServer directly."""

    def __init__(self, server: BrokerServer, identity: str) -> None:
        self.server = server
        self.identity = identity
        self._req_counter = 0
        # Register as a client so we receive pushes
        self.server.connect(identity, self._on_push)
        self._current_conversation: str | None = None

    def _next_id(self) -> str:
        self._req_counter += 1
        return f"repl-{self._req_counter}"

    def _request(self, msg: dict) -> dict:
        msg["id"] = self._next_id()
        result = self.server.handle_request(self.identity, msg)
        if result["type"] == "error":
            raise ValueError(result["message"])
        return result["data"]

    def _on_push(self, msg: dict) -> None:
        """Handle pushed messages — print if in the right conversation."""
        cid = msg.get("conversation_id")
        if cid == self._current_conversation:
            if msg["type"] == "message":
                print(f"\n{format_message(msg['message'])}")
            elif msg["type"] == "system":
                print(f"\n  * {msg['identity']} {msg['event']}ed" if msg['event'] == 'join' else f"\n  * {msg['identity']} left")

    def lobby_loop(self) -> None:
        """Run the lobby REPL loop."""
        while True:
            try:
                line = input("broker> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            parts = line.split(None, 1)
            command = parts[0].lower()
            try:
                if command == "exit":
                    return
                elif command == "list":
                    result = self._request({"type": "list_conversations"})
                    convs = result["conversations"]
                    if not convs:
                        print("  No conversations.")
                    else:
                        for conv in convs:
                            print(format_conversation_line(conv))
                elif command == "create":
                    if len(parts) < 2:
                        print("Usage: create <topic>", file=sys.stderr)
                        continue
                    try:
                        seed = input("  Seed message (Enter to skip): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        continue
                    msg = {"type": "create_conversation", "topic": parts[1]}
                    if seed:
                        msg["content"] = seed
                    result = self._request(msg)
                    print(f"  Created {result['conversation_id']}")
                elif command == "join":
                    if len(parts) < 2:
                        print("Usage: join <id>", file=sys.stderr)
                        continue
                    cid = parts[1].strip()
                    self._request({"type": "join_conversation", "conversation_id": cid})
                    self._current_conversation = cid
                    # Show history on join
                    result = self._request({"type": "history", "conversation_id": cid})
                    for msg in result["messages"]:
                        print(format_message(msg))
                    self._conversation_loop(cid)
                    self._current_conversation = None
                elif command == "help":
                    print(LOBBY_HELP)
                else:
                    print(f"Unknown command: {command}. Type 'help' for options.", file=sys.stderr)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)

    def _conversation_loop(self, conversation_id: str) -> None:
        """Run the conversation REPL loop."""
        while True:
            try:
                line = input(f"{conversation_id}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            command = line.lower()
            try:
                if command == "back":
                    return
                elif command == "leave":
                    self._request({"type": "leave_conversation", "conversation_id": conversation_id})
                    print(f"  Left {conversation_id}")
                    return
                elif command == "read":
                    result = self._request({"type": "history", "conversation_id": conversation_id})
                    for msg in result["messages"]:
                        print(format_message(msg))
                elif command == "members":
                    result = self._request({"type": "list_members", "conversation_id": conversation_id})
                    for member in result["members"]:
                        print(f"  {member}")
                elif command == "close":
                    self._request({"type": "close_conversation", "conversation_id": conversation_id})
                    print(f"  Closed {conversation_id}")
                    return
                elif command == "help":
                    print(CONVERSATION_HELP)
                else:
                    result = self._request({
                        "type": "send_message", "conversation_id": conversation_id, "content": line,
                    })
                    print(f"  Sent {result['message_id']}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)


async def run_server_mode(identity: str, storage_dir: Path, sock_path: str) -> None:
    """Start the socket server and run the REPL."""
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)
    print(f"Broker server listening on {sock_path}")

    repl = ServerREPL(server, identity)
    try:
        # Run REPL in a thread so it doesn't block the event loop
        await asyncio.get_event_loop().run_in_executor(None, repl.lobby_loop)
    finally:
        srv.close()
        await srv.wait_closed()
        Path(sock_path).unlink(missing_ok=True)


def main() -> None:
    """Parse CLI args and start the REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive REPL for the MCP message broker"
    )
    parser.add_argument(
        "--identity", default="user",
        help="Identity for this session (default: user)",
    )
    parser.add_argument(
        "--server", action="store_true",
        help="Run as the broker server (starts socket + REPL)",
    )
    parser.add_argument(
        "--storage-dir", type=Path,
        default=Path.home() / ".mcp-broker" / "conversations",
        help="Directory for conversation files (default: ~/.mcp-broker/conversations)",
    )
    parser.add_argument(
        "--socket", type=str,
        default=str(Path.home() / ".mcp-broker" / "broker.sock"),
        help="Path to broker socket (default: ~/.mcp-broker/broker.sock)",
    )
    args = parser.parse_args()

    if args.server:
        asyncio.run(run_server_mode(args.identity, args.storage_dir, args.socket))
    else:
        # Client mode — not implemented in this task
        print("Client mode not yet implemented. Use --server to start the broker.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify --help works**

Run: `python scripts/broker_cli.py --help`
Expected: Shows `--server`, `--identity`, `--storage-dir`, `--socket` options.

- [ ] **Step 3: Run existing format helper tests**

The `format_conversation_line` and `format_message` functions are unchanged. Run existing tests:

Run: `python -m pytest tests/test_broker_cli.py::test_format_conversation_line_basic tests/test_broker_cli.py::test_format_message_basic -v`
Expected: PASS (format helpers unchanged).

- [ ] **Step 4: Commit**

```bash
git add scripts/broker_cli.py
git commit -m "Rewrite broker_cli with server mode using BrokerServer and socket transport"
```

---

### Task 8: broker_cli.py — client mode

**Files:**
- Modify: `scripts/broker_cli.py`

Add client mode that connects to an existing socket server via BrokerClient.

- [ ] **Step 1: Add ClientREPL class to broker_cli.py**

Add a `ClientREPL` class similar to `ServerREPL` but using `BrokerClient` (async) instead of `BrokerServer` (sync). The client REPL uses `asyncio.run` for each request and monitors the `on_push` queue for real-time messages.

```python
class ClientREPL:
    """REPL that connects to a running broker server via socket."""

    def __init__(self, client: BrokerClient) -> None:
        self.client = client
        self._current_conversation: str | None = None

    # Similar lobby_loop and _conversation_loop as ServerREPL,
    # but calls are async: asyncio.get_event_loop().run_until_complete(self.client.method(...))
```

Replace the `else` branch in `main()`:

```python
    else:
        asyncio.run(run_client_mode(args.identity, args.socket))
```

With:

```python
async def run_client_mode(identity: str, sock_path: str) -> None:
    """Connect to an existing broker server and run the REPL."""
    client = BrokerClient(identity=identity, sock_path=sock_path)
    try:
        await client.connect()
    except (ConnectionRefusedError, FileNotFoundError):
        print(f"Error: Cannot connect to broker at {sock_path}. Is the broker server running?", file=sys.stderr)
        sys.exit(1)

    print(f"Connected to broker at {sock_path}")
    repl = ClientREPL(client)
    try:
        await asyncio.get_event_loop().run_in_executor(None, repl.lobby_loop)
    finally:
        await client.close()
```

- [ ] **Step 2: Verify client mode shows error when no server is running**

Run: `python scripts/broker_cli.py --identity test`
Expected: Error message about not being able to connect.

- [ ] **Step 3: Commit**

```bash
git add scripts/broker_cli.py
git commit -m "Add client mode to broker_cli for connecting to existing server"
```

---

### Task 9: End-to-end integration test

**Files:**
- Create: `tests/test_broker_e2e.py`

- [ ] **Step 1: Write end-to-end test**

Create `tests/test_broker_e2e.py`:

```python
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.mark.asyncio
async def test_full_conversation_flow(tmp_path):
    """End-to-end: server + two clients, create/join/send/read/leave/close."""
    sock_path = str(tmp_path / "test.sock")
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        # Alice creates a conversation with a seed
        result = await alice.create_conversation("Design review", content="Please review the PR")
        cid = result["conversation_id"]

        # Bob joins
        await bob.join_conversation(cid)

        # Bob gets history (should include seed message)
        history = await bob.history(cid)
        contents = [m["content"] for m in history["messages"] if m["sender"] != "system"]
        assert "Please review the PR" in contents

        # Bob sends a message
        await bob.send_message(cid, "LGTM, merging now")
        await asyncio.sleep(0.05)

        # Alice should have received the push
        alice_msgs = alice.get_new_messages(cid)
        pushed_contents = [m["message"]["content"] for m in alice_msgs if m["type"] == "message"]
        assert "LGTM, merging now" in pushed_contents

        # List members
        members = await alice.list_members(cid)
        assert sorted(members["members"]) == ["alice", "bob"]

        # Bob leaves
        await bob.leave_conversation(cid)
        await asyncio.sleep(0.05)

        # Alice should get leave system event
        alice_msgs = alice.get_new_messages(cid)
        leave_events = [m for m in alice_msgs if m["type"] == "system" and m["event"] == "leave"]
        assert any(e["identity"] == "bob" for e in leave_events)

        # Alice closes the conversation
        await alice.close_conversation(cid)

        # Sending to closed fails
        with pytest.raises(ValueError, match="closed"):
            await bob.send_message(cid, "Too late")

        # List shows closed
        convs = await alice.list_conversations(status="closed")
        assert len(convs["conversations"]) == 1

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_broker_e2e.py -v`
Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --ignore=tests/test_install_plugin.py`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_broker_e2e.py
git commit -m "Add end-to-end integration test for socket-based broker"
```
