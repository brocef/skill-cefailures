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
