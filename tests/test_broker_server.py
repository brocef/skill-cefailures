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
