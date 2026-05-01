import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer


def test_server_initializes_dm_storage(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
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
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    data = _send(server, "alice", to=["bob"], content="hello bob")
    assert "message_id" in data
    lines, _ = server.inbox_log.read_from("bob", 0)
    assert len(lines) == 1
    assert "[alice]" in lines[0]
    assert lines[0].endswith("hello bob")


def test_send_dm_delivers_to_multiple_recipients(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob", "carol"], content="group ping")
    bob_lines, _ = server.inbox_log.read_from("bob", 0)
    carol_lines, _ = server.inbox_log.read_from("carol", 0)
    assert len(bob_lines) == 1 and len(carol_lines) == 1
    assert " → " in bob_lines[0]  # multi-recipient arrow present


def test_send_dm_writes_sender_outbox(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    _send(server, "alice", to=["bob"], content="audit me")
    sent = server.outbox_log.read_all("alice")
    assert len(sent) == 1
    assert "audit me" in sent[0]


def test_send_dm_rejects_broadcast_sentinel(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    with pytest.raises(ValueError, match="BROADCAST"):
        _send(server, "alice", to=["BROADCAST"], content="nope")


def test_send_dm_pushes_to_connected_recipient(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    received: list[dict] = []
    server.connect("alice", lambda m: None)
    server.connect("bob", received.append)
    _send(server, "alice", to=["bob"], content="live push")
    assert any(m.get("type") == "inbox_message" for m in received)


def _broadcast(server: BrokerServer, identity: str, content: str) -> dict:
    result = server.handle_request(identity, {"type": "send_broadcast", "id": "x", "content": content})
    if result["type"] == "error":
        raise ValueError(result["message"])
    return result["data"]


def test_broadcast_delivers_to_every_registered_identity(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    server.connect("carol", lambda m: None)
    # Register all three by having each send a DM.
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "seed"})
    server.handle_request("bob", {"type": "send_dm", "id": "2", "to": ["carol"], "content": "seed"})
    server.handle_request("carol", {"type": "send_dm", "id": "3", "to": ["alice"], "content": "seed"})

    _broadcast(server, "alice", "announcement")
    for recipient in ("alice", "bob", "carol"):
        lines, _ = server.inbox_log.read_from(recipient, 0)
        assert any("→ BROADCAST" in line and line.endswith("announcement") for line in lines)


def test_broadcast_writes_sender_outbox(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["alice"], "content": "self"})
    _broadcast(server, "alice", "hello world")
    sent = server.outbox_log.read_all("alice")
    assert any("→ BROADCAST" in line for line in sent)


def test_reply_all_computes_recipient_set(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.connect("bob", lambda m: None)
    server.connect("carol", lambda m: None)
    sent = server.handle_request("alice", {
        "type": "send_dm", "id": "1", "to": ["bob", "carol"], "content": "kickoff",
    })["data"]
    orig_id = sent["message_id"]

    result = server.handle_request("bob", {
        "type": "reply_all", "id": "2", "to_message": orig_id, "content": "replying",
    })
    assert result["type"] == "response"
    assert set(result["data"]["recipients"]) == {"alice", "carol"}

    alice_lines, _ = server.inbox_log.read_from("alice", 0)
    carol_lines, _ = server.inbox_log.read_from("carol", 0)
    bob_lines, _ = server.inbox_log.read_from("bob", 0)
    assert any(line.endswith("replying") for line in alice_lines)
    assert any(line.endswith("replying") for line in carol_lines)
    assert not any(line.endswith("replying") for line in bob_lines)


def test_reply_all_rejects_broadcast_message(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "seed", "to": ["alice"], "content": "s"})
    bcast = server.handle_request("alice", {"type": "send_broadcast", "id": "1", "content": "hi all"})
    result = server.handle_request("alice", {
        "type": "reply_all", "id": "2", "to_message": bcast["data"]["message_id"], "content": "nope",
    })
    assert result["type"] == "error"
    assert "broadcast" in result["message"].lower()


def test_reply_all_unknown_message_errors(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    result = server.handle_request("alice", {
        "type": "reply_all", "id": "2", "to_message": "msg-does-not-exist", "content": "x",
    })
    assert result["type"] == "error"
    assert "not found" in result["message"].lower()


def test_history_inbox_returns_all_without_advancing_cursor(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "first"})
    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "second"})

    before_cursor = server.cursors.get("bob")
    result = server.handle_request("bob", {"type": "history_inbox", "id": "x"})
    assert result["type"] == "response"
    lines = result["data"]["lines"]
    assert len(lines) == 2
    assert server.cursors.get("bob") == before_cursor


def test_history_inbox_filters_by_sender(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.connect("carol", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "from alice"})
    server.handle_request("carol", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "from carol"})

    result = server.handle_request("bob", {"type": "history_inbox", "id": "x", "from": "alice"})
    lines = result["data"]["lines"]
    assert len(lines) == 1
    assert "from alice" in lines[0]


def test_history_sent_reads_outbox(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "sent 1"})
    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["carol"], "content": "sent 2"})

    result = server.handle_request("alice", {"type": "history_inbox", "id": "x", "sent": True})
    lines = result["data"]["lines"]
    assert len(lines) == 2
    assert any("sent 1" in line for line in lines)
    assert any("sent 2" in line for line in lines)


def test_read_inbox_advances_cursor_and_returns_only_new(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    server.handle_request("alice", {"type": "send_dm", "id": "1", "to": ["bob"], "content": "one"})

    first = server.handle_request("bob", {"type": "read_inbox", "id": "x"})
    assert len(first["data"]["lines"]) == 1

    second = server.handle_request("bob", {"type": "read_inbox", "id": "y"})
    assert second["data"]["lines"] == []

    server.handle_request("alice", {"type": "send_dm", "id": "2", "to": ["bob"], "content": "two"})
    third = server.handle_request("bob", {"type": "read_inbox", "id": "z"})
    assert len(third["data"]["lines"]) == 1
    assert third["data"]["lines"][0].endswith("two")


def test_broadcast_identity_cannot_be_claimed(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    with pytest.raises(ValueError, match="reserved"):
        server.connect("BROADCAST", lambda m: None)


def test_orchestrator_identity_can_be_claimed_without_token(tmp_path: Path) -> None:
    """v1.5.0 option 3: orchestrator identities are name-reservations, not auth-gated."""
    server = BrokerServer(root_dir=tmp_path)
    # No token file, no token argument — should still succeed.
    server.connect("@orchestrator/myorg", lambda m: None)
    assert "@orchestrator/myorg" in server.clients


def test_human_identity_can_be_claimed_without_token(tmp_path: Path) -> None:
    """`human` is a name-reservation; no token required after option 3."""
    server = BrokerServer(root_dir=tmp_path)
    server.connect("human", lambda m: None)
    assert "human" in server.clients


def test_message_id_length_matches_column_width(tmp_path: Path) -> None:
    """If _generate_id ever changes, MID_COLUMN_WIDTH in broker_cli.py must update too."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from broker_cli import MID_COLUMN_WIDTH

    server = BrokerServer(root_dir=tmp_path)
    mid = server._message_id()
    assert len(mid) == MID_COLUMN_WIDTH, (
        f"_message_id() produces {len(mid)}-char IDs but MID_COLUMN_WIDTH is "
        f"{MID_COLUMN_WIDTH}. Update one or the other to match."
    )


def test_follow_connect_populates_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    assert "alice" in server.clients
    assert "alice" in server.followers
    assert "since" in server.followers["alice"]


def test_oneshot_connect_does_not_populate_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    assert "alice" in server.clients
    assert "alice" not in server.followers


def test_default_mode_is_oneshot(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    assert "alice" in server.clients
    assert "alice" not in server.followers


def test_disconnect_removes_from_both_maps(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.disconnect("alice")
    assert "alice" not in server.clients
    assert "alice" not in server.followers


def test_second_follower_rejected(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    with pytest.raises(ValueError, match="already has an active follower"):
        server.connect("alice", lambda m: None, mode="follow")


def test_oneshot_during_active_follow_allowed(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.connect("alice", lambda m: None, mode="oneshot")  # must not raise
    assert "alice" in server.followers  # follower slot intact


def test_rejected_second_follow_preserves_first_callback(tmp_path: Path) -> None:
    """A rejected second follow must not clobber the first follower's callback or `since`."""
    server = BrokerServer(root_dir=tmp_path)
    first = lambda m: None
    second = lambda m: None
    server.connect("alice", first, mode="follow")
    since_before = server.followers["alice"]["since"]
    with pytest.raises(ValueError):
        server.connect("alice", second, mode="follow")
    assert server.clients["alice"] is first
    assert server.followers["alice"]["since"] == since_before


def test_list_clients_live_only_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.connect("bob", lambda m: None, mode="oneshot")
    data = server._handle_list_clients("alice", {})
    live_ids = [e["identity"] for e in data["live"]]
    offline_ids = [e["identity"] for e in data["offline"]]
    assert live_ids == ["alice"]
    assert "bob" in offline_ids
    assert data["live"][0]["mode"] == "follow"
    assert "since" in data["live"][0]
    assert "alice" not in offline_ids


def test_list_clients_offline_uses_registry(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    server.disconnect("alice")
    data = server._handle_list_clients("system", {})
    offline_ids = [e["identity"] for e in data["offline"]]
    assert "alice" in offline_ids
    entry = next(e for e in data["offline"] if e["identity"] == "alice")
    assert "lastSeenAt" in entry


def test_list_clients_case_insensitive_difference(tmp_path: Path) -> None:
    """Follower 'Alice' (mixed case) must not appear in offline as 'alice'."""
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    server.disconnect("alice")
    server.connect("Alice", lambda m: None, mode="follow")
    data = server._handle_list_clients("system", {})
    live_ids = [e["identity"] for e in data["live"]]
    offline_ids = [e["identity"] for e in data["offline"]]
    assert "Alice" in live_ids
    # Despite registry holding 'alice' (lowercased key, canonical 'alice'), it must not be reported as offline.
    assert all(i.lower() != "alice" for i in offline_ids)


def test_list_clients_sorted_by_identity(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("zeta", lambda m: None, mode="follow")
    server.connect("alpha", lambda m: None, mode="follow")
    data = server._handle_list_clients("system", {})
    live_ids = [e["identity"] for e in data["live"]]
    assert live_ids == ["alpha", "zeta"]
