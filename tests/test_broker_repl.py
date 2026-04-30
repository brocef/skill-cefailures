"""Unit tests for the in-server interactive REPL (ServerREPL)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_cli import ServerREPL
from broker_server import BrokerServer


def _make_repl(tmp_path: Path) -> ServerREPL:
    server = BrokerServer(root_dir=tmp_path)
    return ServerREPL(server, identity="user")


def test_who_lists_connected_identities(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("alice", lambda m: None)
    repl.server.connect("bob", lambda m: None)
    assert repl._dispatch("who") is True
    out = capsys.readouterr().out
    assert "alice" in out and "bob" in out and "user" in out


def test_send_dm_via_repl(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("bob", lambda m: None)
    assert repl._dispatch("send bob hello there") is True
    out = capsys.readouterr().out
    assert "sent msg-" in out
    lines, _ = repl.server.inbox_log.read_from("bob", 0)
    assert any("hello there" in line for line in lines)


def test_send_dm_to_multiple_recipients(tmp_path: Path) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("alice", lambda m: None)
    repl.server.connect("bob", lambda m: None)
    repl._dispatch("send alice,bob ping team")
    a, _ = repl.server.inbox_log.read_from("alice", 0)
    b, _ = repl.server.inbox_log.read_from("bob", 0)
    assert any("ping team" in line for line in a)
    assert any("ping team" in line for line in b)


def test_broadcast_via_repl(tmp_path: Path) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("alice", lambda m: None)
    repl.server.connect("bob", lambda m: None)
    repl._dispatch("broadcast all-hands meeting")
    a, _ = repl.server.inbox_log.read_from("alice", 0)
    assert any("BROADCAST" in line and "all-hands meeting" in line for line in a)


def test_emit_messages_toggle_off_by_default(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("bob", lambda m: None)
    repl._dispatch("send bob nope")
    out = capsys.readouterr().out
    # No '[audit]' line because emit-messages is off.
    assert "[audit]" not in out


def test_emit_messages_on_taps_audit_hook(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("bob", lambda m: None)
    repl._dispatch("emit-messages on")
    repl._dispatch("send bob audited")
    out = capsys.readouterr().out
    assert "[audit]" in out
    assert "audited" in out


def test_emit_messages_off_silences_audit(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("bob", lambda m: None)
    repl._dispatch("emit-messages on")
    capsys.readouterr()  # discard
    repl._dispatch("emit-messages off")
    repl._dispatch("send bob silent")
    out = capsys.readouterr().out
    assert "[audit]" not in out


def test_help_lists_dm_commands(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl._dispatch("help")
    out = capsys.readouterr().out
    for cmd in ("who", "send", "broadcast", "read", "history", "emit-messages"):
        assert cmd in out


def test_exit_returns_false(tmp_path: Path) -> None:
    repl = _make_repl(tmp_path)
    assert repl._dispatch("exit") is False


def test_unknown_command_does_not_exit(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    assert repl._dispatch("nonsense") is True
    err = capsys.readouterr().err
    assert "Unknown command" in err
