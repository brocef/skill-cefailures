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


def test_send_subcommand(running_server):
    """'broker send' sends a message and prints JSON."""
    server, sock, loop = running_server
    from broker_cli import run_oneshot

    result = loop.run_until_complete(
        run_oneshot(sock, "agent_a", "create_conversation", {"topic": "Test"})
    )
    cid = result["conversation_id"]

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

    # Use the server directly because run_oneshot disconnects after each
    # call, which removes the identity from all member sets.
    cid = _create_conversation(server, "agent_a", "Test")
    server.handle_request("agent_b", {"type": "join_conversation", "conversation_id": cid, "id": "j"})

    result = server.handle_request("agent_a", {"type": "list_members", "conversation_id": cid, "id": "m"})
    assert sorted(result["data"]["members"]) == ["agent_a", "agent_b"]


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


# ---------------------------------------------------------------------------
# _run_and_print output tests
# ---------------------------------------------------------------------------

def test_run_and_print_stdout(running_server, capsys):
    """_run_and_print prints JSON to stdout."""
    server, sock, loop = running_server
    from broker_cli import _run_and_print

    # _run_and_print calls asyncio.run() which creates a new event loop,
    # but the server is running on the fixture's loop.  Patch asyncio.run
    # to use the fixture's loop instead.
    with patch("broker_cli.asyncio.run", side_effect=lambda coro: loop.run_until_complete(coro)):
        _run_and_print(sock, "agent_a", "create_conversation", {"topic": "Test"})
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "conversation_id" in data
    assert data["topic"] == "Test"


def test_run_and_print_error(running_server, capsys):
    """_run_and_print prints error JSON to stderr and exits 1 on error."""
    server, sock, loop = running_server
    from broker_cli import _run_and_print

    # Patch asyncio.run to use the fixture's event loop.
    with patch("broker_cli.asyncio.run", side_effect=lambda coro: loop.run_until_complete(coro)):
        with pytest.raises(SystemExit) as exc_info:
            _run_and_print(sock, "agent_a", "send_message", {
                "conversation_id": "nonexistent", "content": "Hello",
            })
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    err_data = json.loads(captured.err)
    assert "error" in err_data
    assert "not found" in err_data["error"]


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

        # Run the CLI as a subprocess, parsing its compact output.
        # Use asyncio.to_thread so the server event loop keeps accepting connections
        # while the subprocess (itself a client) makes its request.
        broker_cli = str(Path(__file__).parent.parent / "scripts" / "broker_cli.py")
        out = await asyncio.to_thread(
            subprocess.run,
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
