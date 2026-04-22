import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer


def test_server_initializes_dm_storage(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    assert server.inbox_log.base_dir == tmp_path / "inbox"
    assert server.outbox_log.base_dir == tmp_path / "outbox"
    assert server.cursors.base_dir == tmp_path / "cursors"
    assert server.registry.path == tmp_path / "identities.json"


def _send(server: BrokerServer, identity: str, **kwargs) -> dict:
    """Helper that invokes handle_request and unwraps the data/error."""
    result = server.handle_request(identity, {"type": "send_dm", "id": "req-x", **kwargs})
    if result["type"] == "error":
        raise ValueError(result["message"])
    return result["data"]


def test_send_dm_delivers_to_single_recipient(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    data = _send(server, "alice", to=["bob"], content="hello bob")
    assert "message_id" in data
    lines, _ = server.inbox_log.read_from("bob", 0)
    assert len(lines) == 1
    assert "[alice]" in lines[0]
    assert lines[0].endswith("hello bob")


def test_send_dm_delivers_to_multiple_recipients(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob", "carol"], content="group ping")
    bob_lines, _ = server.inbox_log.read_from("bob", 0)
    carol_lines, _ = server.inbox_log.read_from("carol", 0)
    assert len(bob_lines) == 1 and len(carol_lines) == 1
    assert " → " in bob_lines[0]  # multi-recipient arrow present


def test_send_dm_writes_sender_outbox(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob"], content="audit me")
    sent = server.outbox_log.read_all("alice")
    assert len(sent) == 1
    assert "audit me" in sent[0]


def test_send_dm_rejects_broadcast_sentinel(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    server.connect("alice", lambda m: None)
    with pytest.raises(ValueError, match="BROADCAST"):
        _send(server, "alice", to=["BROADCAST"], content="nope")


def test_send_dm_pushes_to_connected_recipient(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    received: list[dict] = []
    server.connect("alice", lambda m: None)
    server.connect("bob", received.append)
    _send(server, "alice", to=["bob"], content="live push")
    assert any(m.get("type") == "inbox_message" for m in received)
