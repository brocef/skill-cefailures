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
    non_system = [m for m in server.conversations[cid]["messages"] if m["sender"] != "system"]
    assert len(non_system) == 1
    assert non_system[0]["content"] == "Seed message"


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


# --- Task 2: Membership and message routing ---


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


# --- Task 2: System messages ---


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


# --- Task 2: Leave, close, history, list_members, not_found, persistence ---


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
