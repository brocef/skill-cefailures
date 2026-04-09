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
