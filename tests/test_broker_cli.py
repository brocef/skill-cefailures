import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_cli import (
    conversation_loop,
    format_conversation_line,
    format_message,
    lobby_loop,
)
from mcp_broker import ConversationStore


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

def test_module_imports() -> None:
    """broker_cli can be imported without errors."""
    import broker_cli  # noqa: F811
    assert hasattr(broker_cli, "main")
    assert hasattr(broker_cli, "lobby_loop")
    assert hasattr(broker_cli, "conversation_loop")


# ---------------------------------------------------------------------------
# --help via subprocess
# ---------------------------------------------------------------------------

def test_help_flag() -> None:
    """Running broker_cli.py --help exits 0 and shows usage."""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "scripts" / "broker_cli.py"), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Interactive REPL" in result.stdout


# ---------------------------------------------------------------------------
# format_conversation_line
# ---------------------------------------------------------------------------

def test_format_conversation_line_basic() -> None:
    """format_conversation_line produces the expected display string."""
    conv = {
        "id": "a1b2c3",
        "topic": "Design review",
        "status": "open",
        "message_count": 3,
        "unread_count": 1,
    }
    line = format_conversation_line(conv)
    assert line == '  [a1b2c3] "Design review" (open, 3 msgs, 1 unread)'


def test_format_conversation_line_closed() -> None:
    """format_conversation_line works for closed conversations."""
    conv = {
        "id": "xyz789",
        "topic": "Old chat",
        "status": "closed",
        "message_count": 10,
        "unread_count": 0,
    }
    line = format_conversation_line(conv)
    assert "(closed," in line
    assert "10 msgs" in line
    assert "0 unread" in line


def test_format_conversation_line_zero_messages() -> None:
    """format_conversation_line handles zero messages."""
    conv = {
        "id": "empty1",
        "topic": "Empty",
        "status": "open",
        "message_count": 0,
        "unread_count": 0,
    }
    line = format_conversation_line(conv)
    assert "0 msgs" in line
    assert "0 unread" in line


# ---------------------------------------------------------------------------
# format_message
# ---------------------------------------------------------------------------

def test_format_message_basic() -> None:
    """format_message produces the expected display string."""
    msg = {"sender": "agent_a", "content": "Sure, I'll start with the config"}
    line = format_message(msg)
    assert line == "  [agent_a] Sure, I'll start with the config"


def test_format_message_preserves_content() -> None:
    """format_message preserves the full message content."""
    msg = {"sender": "bob", "content": "Line one\nLine two"}
    line = format_message(msg)
    assert "[bob]" in line
    assert "Line one\nLine two" in line


# ---------------------------------------------------------------------------
# lobby_loop integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path: Path) -> ConversationStore:
    """Create a ConversationStore with a temp storage directory."""
    return ConversationStore(identity="testuser", storage_dir=tmp_path)


def test_lobby_list_empty(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'list' command prints no-conversations message when empty."""
    with patch("builtins.input", side_effect=["list", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert "No conversations" in output


def test_lobby_list_shows_conversations(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'list' command shows created conversations."""
    store.create_conversation("My topic")
    with patch("builtins.input", side_effect=["list", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert '"My topic"' in output
    assert "open" in output


def test_lobby_create_without_seed(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' with empty seed creates a conversation."""
    with patch("builtins.input", side_effect=["create Test topic", "", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert "Created" in output
    convs = store.list_conversations()["conversations"]
    assert len(convs) == 1
    assert convs[0]["topic"] == "Test topic"


def test_lobby_create_with_seed(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' with a seed message sends the seed."""
    with patch("builtins.input", side_effect=["create Design caching", "Add Redis", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert "Created" in output
    assert "Sent msg-" in output
    convs = store.list_conversations()["conversations"]
    assert len(convs) == 1
    assert convs[0]["message_count"] == 1


def test_lobby_create_missing_topic(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' without a topic prints usage to stderr."""
    with patch("builtins.input", side_effect=["create", "exit"]):
        lobby_loop(store)
    err = capsys.readouterr().err
    assert "Usage" in err


def test_lobby_help(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'help' prints available commands."""
    with patch("builtins.input", side_effect=["help", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert "list" in output
    assert "create" in output
    assert "join" in output


def test_lobby_unknown_command(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby prints error for unknown commands."""
    with patch("builtins.input", side_effect=["foobar", "exit"]):
        lobby_loop(store)
    err = capsys.readouterr().err
    assert "Unknown command" in err


def test_lobby_eof_exits(store: ConversationStore) -> None:
    """Lobby exits cleanly on EOFError."""
    with patch("builtins.input", side_effect=EOFError):
        lobby_loop(store)  # Should not raise


def test_lobby_keyboard_interrupt_exits(store: ConversationStore) -> None:
    """Lobby exits cleanly on KeyboardInterrupt."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        lobby_loop(store)  # Should not raise


def test_lobby_join_nonexistent(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'join' with bad ID prints error."""
    with patch("builtins.input", side_effect=["join badid", "exit"]):
        lobby_loop(store)
    err = capsys.readouterr().err
    assert "not found" in err


# ---------------------------------------------------------------------------
# conversation_loop integration tests
# ---------------------------------------------------------------------------

def test_conversation_send_message(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Typing text in conversation mode sends a message."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    with patch("builtins.input", side_effect=["Hello world", "back"]):
        conversation_loop(store, cid)
    output = capsys.readouterr().out
    assert "Sent msg-" in output


def test_conversation_read_messages(store: ConversationStore, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """'read' command in conversation shows new messages."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    other = ConversationStore(identity="other", storage_dir=tmp_path)
    other.send_message(cid, "Hello from other")
    with patch("builtins.input", side_effect=["read", "back"]):
        conversation_loop(store, cid)
    output = capsys.readouterr().out
    assert "[other]" in output
    assert "Hello from other" in output


def test_conversation_close(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """'close' command closes the conversation and returns."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    with patch("builtins.input", side_effect=["close"]):
        conversation_loop(store, cid)
    output = capsys.readouterr().out
    assert f"Closed {cid}" in output
    convs = store.list_conversations(status="closed")["conversations"]
    assert len(convs) == 1


def test_conversation_help(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """'help' command in conversation shows available commands."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    with patch("builtins.input", side_effect=["help", "back"]):
        conversation_loop(store, cid)
    output = capsys.readouterr().out
    assert "read" in output
    assert "close" in output
    assert "back" in output


def test_conversation_back(store: ConversationStore) -> None:
    """'back' command returns from conversation loop."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    with patch("builtins.input", side_effect=["back"]):
        conversation_loop(store, cid)  # Should return without error


def test_conversation_eof_exits(store: ConversationStore) -> None:
    """Conversation loop exits cleanly on EOFError."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    with patch("builtins.input", side_effect=EOFError):
        conversation_loop(store, cid)  # Should not raise


def test_conversation_send_to_closed_prints_error(store: ConversationStore, capsys: pytest.CaptureFixture) -> None:
    """Sending a message to a closed conversation prints an error."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    store.close_conversation(cid)
    with patch("builtins.input", side_effect=["some message", "back"]):
        conversation_loop(store, cid)
    err = capsys.readouterr().err
    assert "closed" in err


# ---------------------------------------------------------------------------
# Join shows unread on entry
# ---------------------------------------------------------------------------

def test_join_shows_unread(store: ConversationStore, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Joining a conversation automatically shows unread messages."""
    created = store.create_conversation("Topic")
    cid = created["conversation_id"]
    other = ConversationStore(identity="other", storage_dir=tmp_path)
    other.send_message(cid, "Unread message")
    with patch("builtins.input", side_effect=[f"join {cid}", "back", "exit"]):
        lobby_loop(store)
    output = capsys.readouterr().out
    assert "[other]" in output
    assert "Unread message" in output
