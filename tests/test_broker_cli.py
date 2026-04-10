import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_cli import (
    ServerREPL,
    format_conversation_line,
    format_message,
)
from broker_server import BrokerServer


# ---------------------------------------------------------------------------
# Module import
# ---------------------------------------------------------------------------

def test_module_imports() -> None:
    """broker_cli can be imported without errors."""
    import broker_cli  # noqa: F811
    assert hasattr(broker_cli, "main")
    assert hasattr(broker_cli, "ServerREPL")


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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def server(tmp_path: Path) -> BrokerServer:
    """Create a BrokerServer with a temp storage directory."""
    return BrokerServer(storage_dir=tmp_path)


@pytest.fixture
def repl(server: BrokerServer) -> ServerREPL:
    """Create a ServerREPL using the test server."""
    return ServerREPL(server, "testuser")


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
    """Start a broker server in a background task, yield (server, sock_path, loop), then shut down."""
    from broker_server import start_server

    server = BrokerServer(storage_dir=tmp_path)
    loop = asyncio.new_event_loop()
    srv = loop.run_until_complete(start_server(server, sock_path))
    yield server, sock_path, loop
    srv.close()
    loop.run_until_complete(srv.wait_closed())
    loop.close()


def _create_conversation(server: BrokerServer, identity: str, topic: str, content: str | None = None) -> str:
    """Helper to create a conversation and return its ID."""
    msg: dict = {"type": "create_conversation", "topic": topic, "id": "setup"}
    if content:
        msg["content"] = content
    result = server.handle_request(identity, msg)
    return result["data"]["conversation_id"]


# ---------------------------------------------------------------------------
# lobby_loop integration tests
# ---------------------------------------------------------------------------

def test_lobby_list_empty(repl: ServerREPL, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'list' command prints no-conversations message when empty."""
    with patch("builtins.input", side_effect=["list", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "No conversations" in output


def test_lobby_list_shows_conversations(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'list' command shows created conversations."""
    _create_conversation(server, "testuser", "My topic")
    with patch("builtins.input", side_effect=["list", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert '"My topic"' in output
    assert "open" in output


def test_lobby_create_without_seed(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' with empty seed creates a conversation."""
    with patch("builtins.input", side_effect=["create Test topic", "", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "Created" in output
    result = server.handle_request("testuser", {"type": "list_conversations", "id": "check"})
    convs = result["data"]["conversations"]
    assert len(convs) == 1
    assert convs[0]["topic"] == "Test topic"


def test_lobby_create_with_seed(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' with a seed message sends the seed."""
    with patch("builtins.input", side_effect=["create Design caching", "Add Redis", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "Created" in output
    result = server.handle_request("testuser", {"type": "list_conversations", "id": "check"})
    convs = result["data"]["conversations"]
    assert len(convs) == 1
    assert convs[0]["message_count"] == 1


def test_lobby_create_missing_topic(repl: ServerREPL, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'create' without a topic prints usage to stderr."""
    with patch("builtins.input", side_effect=["create", "exit"]):
        repl.lobby_loop()
    err = capsys.readouterr().err
    assert "Usage" in err


def test_lobby_help(repl: ServerREPL, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'help' prints available commands."""
    with patch("builtins.input", side_effect=["help", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "list" in output
    assert "create" in output
    assert "join" in output


def test_lobby_unknown_command(repl: ServerREPL, capsys: pytest.CaptureFixture) -> None:
    """Lobby prints error for unknown commands."""
    with patch("builtins.input", side_effect=["foobar", "exit"]):
        repl.lobby_loop()
    err = capsys.readouterr().err
    assert "Unknown command" in err


def test_lobby_eof_exits(repl: ServerREPL) -> None:
    """Lobby exits cleanly on EOFError."""
    with patch("builtins.input", side_effect=EOFError):
        repl.lobby_loop()  # Should not raise


def test_lobby_keyboard_interrupt_exits(repl: ServerREPL) -> None:
    """Lobby exits cleanly on KeyboardInterrupt."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        repl.lobby_loop()  # Should not raise


def test_lobby_join_nonexistent(repl: ServerREPL, capsys: pytest.CaptureFixture) -> None:
    """Lobby 'join' with bad ID prints error."""
    with patch("builtins.input", side_effect=["join badid", "exit"]):
        repl.lobby_loop()
    err = capsys.readouterr().err
    assert "not found" in err


# ---------------------------------------------------------------------------
# conversation_loop integration tests
# ---------------------------------------------------------------------------

def test_conversation_send_message(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Typing text in conversation mode sends a message."""
    cid = _create_conversation(server, "testuser", "Topic")
    with patch("builtins.input", side_effect=[f"join {cid}", "Hello world", "back", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "Sent msg-" in output


def test_conversation_read_messages(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """'read' command in conversation shows new messages."""
    cid = _create_conversation(server, "testuser", "Topic")
    # Send a message as another user
    server.handle_request("other", {"type": "join_conversation", "conversation_id": cid, "id": "j"})
    server.handle_request("other", {"type": "send_message", "conversation_id": cid, "content": "Hello from other", "id": "s"})
    with patch("builtins.input", side_effect=[f"join {cid}", "read", "back", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "[other]" in output
    assert "Hello from other" in output


def test_conversation_close(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """'close' command closes the conversation and returns."""
    cid = _create_conversation(server, "testuser", "Topic")
    with patch("builtins.input", side_effect=[f"join {cid}", "close", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert f"Closed {cid}" in output
    result = server.handle_request("testuser", {"type": "list_conversations", "status": "closed", "id": "check"})
    convs = result["data"]["conversations"]
    assert len(convs) == 1


def test_conversation_help(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """'help' command in conversation shows available commands."""
    cid = _create_conversation(server, "testuser", "Topic")
    with patch("builtins.input", side_effect=[f"join {cid}", "help", "back", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "read" in output
    assert "close" in output
    assert "back" in output


def test_conversation_back(repl: ServerREPL, server: BrokerServer) -> None:
    """'back' command returns from conversation loop."""
    cid = _create_conversation(server, "testuser", "Topic")
    with patch("builtins.input", side_effect=[f"join {cid}", "back", "exit"]):
        repl.lobby_loop()  # Should return without error


def test_conversation_eof_exits(repl: ServerREPL, server: BrokerServer) -> None:
    """Conversation loop exits cleanly on EOFError."""
    cid = _create_conversation(server, "testuser", "Topic")
    with patch("builtins.input", side_effect=[f"join {cid}", EOFError, "exit"]):
        repl.lobby_loop()  # Should not raise


def test_conversation_send_to_closed_prints_error(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Sending a message to a closed conversation prints an error."""
    cid = _create_conversation(server, "testuser", "Topic")
    server.handle_request("testuser", {"type": "close_conversation", "conversation_id": cid, "id": "close"})
    with patch("builtins.input", side_effect=[f"join {cid}", "some message", "back", "exit"]):
        repl.lobby_loop()
    err = capsys.readouterr().err
    assert "closed" in err


# ---------------------------------------------------------------------------
# Join shows unread on entry
# ---------------------------------------------------------------------------

def test_join_shows_unread(repl: ServerREPL, server: BrokerServer, capsys: pytest.CaptureFixture) -> None:
    """Joining a conversation automatically shows unread messages."""
    cid = _create_conversation(server, "testuser", "Topic")
    # Send a message as another user
    server.handle_request("other", {"type": "join_conversation", "conversation_id": cid, "id": "j"})
    server.handle_request("other", {"type": "send_message", "conversation_id": cid, "content": "Unread message", "id": "s"})
    with patch("builtins.input", side_effect=[f"join {cid}", "back", "exit"]):
        repl.lobby_loop()
    output = capsys.readouterr().out
    assert "[other]" in output
    assert "Unread message" in output


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
