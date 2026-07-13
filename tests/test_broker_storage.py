import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_storage import (
    InboxLog,
    OutboxLog,
    CursorStore,
    IdentityRegistry,
    encode_identity,
)


def test_encode_identity_replaces_slash() -> None:
    assert encode_identity("@example/shared") == "@example_shared"
    assert encode_identity("Example-Org/example-mobile") == "Example-Org_example-mobile"
    assert encode_identity("plain") == "plain"


def test_inbox_append_reads_back(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "msg-test", "line one")
    log.append("alice", "msg-test", "line two")
    assert log.path_for("alice").read_text() == "msg-test\tline one\nmsg-test\tline two\n"


def test_inbox_read_from_offset(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "msg-test", "one")
    log.append("alice", "msg-test", "two")
    log.append("alice", "msg-test", "three")
    first_line_end = len("msg-test\tone\n")
    lines, new_offset = log.read_from("alice", offset=first_line_end)
    assert lines == ["msg-test\ttwo", "msg-test\tthree"]
    assert new_offset == len("msg-test\tone\nmsg-test\ttwo\nmsg-test\tthree\n")


def test_inbox_read_empty_for_unknown_identity(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    lines, offset = log.read_from("nobody", offset=0)
    assert lines == []
    assert offset == 0


def test_inbox_partial_trailing_line_not_returned(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    path = log.path_for("alice")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("complete\npartial-no-newline")
    lines, offset = log.read_from("alice", offset=0)
    assert lines == ["complete"]
    assert offset == len("complete\n")


def test_cursor_store_round_trip(tmp_path: Path) -> None:
    store = CursorStore(tmp_path)
    assert store.get("alice") == 0
    store.set("alice", 42)
    assert store.get("alice") == 42
    store2 = CursorStore(tmp_path)
    assert store2.get("alice") == 42


def test_outbox_append(tmp_path: Path) -> None:
    log = OutboxLog(tmp_path)
    log.append("alice", "msg-test", "first sent")
    log.append("alice", "msg-test", "second sent")
    assert log.path_for("alice").read_text() == "msg-test\tfirst sent\nmsg-test\tsecond sent\n"


def test_outbox_read_all(tmp_path: Path) -> None:
    log = OutboxLog(tmp_path)
    log.append("alice", "msg-test", "a")
    log.append("alice", "msg-test", "b")
    assert log.read_all("alice") == ["msg-test\ta", "msg-test\tb"]
    assert log.read_all("nobody") == []


def test_registry_records_first_and_last_seen(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("alice", now="2026-04-22T00:00:00Z", wrote=False)
    reg.touch("alice", now="2026-04-22T00:05:00Z", wrote=True)
    entry = reg.get("alice")
    assert entry["firstSeenAt"] == "2026-04-22T00:00:00Z"
    assert entry["lastSeenAt"] == "2026-04-22T00:05:00Z"
    assert entry["lastWriteAt"] == "2026-04-22T00:05:00Z"


def test_registry_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "identities.json"
    reg = IdentityRegistry(path)
    reg.touch("alice", now="2026-04-22T00:00:00Z", wrote=True)
    reg2 = IdentityRegistry(path)
    assert reg2.get("alice")["firstSeenAt"] == "2026-04-22T00:00:00Z"


def test_registry_list_all(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("alice", now="t1", wrote=False)
    reg.touch("bob", now="t1", wrote=False)
    assert sorted(reg.all()) == ["alice", "bob"]


def test_registry_lookup_case_insensitive(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("Alice", now="2026-04-22T00:00:00Z", wrote=False)
    entry = reg.get("alice")
    assert entry is not None
    assert entry["canonical"] == "Alice"


def test_registry_wrote_false_does_not_set_last_write(tmp_path: Path) -> None:
    reg = IdentityRegistry(tmp_path / "identities.json")
    reg.touch("alice", now="2026-04-22T00:00:00Z", wrote=False)
    entry = reg.get("alice")
    assert "lastWriteAt" not in entry


def test_registry_recovers_from_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "identities.json"
    path.write_text("{not json")
    reg = IdentityRegistry(path)
    reg.touch("alice", now="t1", wrote=True)
    assert reg.get("alice")["firstSeenAt"] == "t1"


def test_inbox_append_prepends_mid_with_tab(tmp_path: Path) -> None:
    inbox = InboxLog(tmp_path)
    inbox.append("alice", "msg-abc123", "2026-04-30T00:00:00Z [bob] hi")
    contents = (tmp_path / "alice.log").read_text()
    assert contents == "msg-abc123\t2026-04-30T00:00:00Z [bob] hi\n"


def test_outbox_append_prepends_mid_with_tab(tmp_path: Path) -> None:
    outbox = OutboxLog(tmp_path)
    outbox.append("alice", "msg-xyz", "2026-04-30T00:00:00Z [alice → bob] hi")
    contents = (tmp_path / "alice.log").read_text()
    assert contents == "msg-xyz\t2026-04-30T00:00:00Z [alice → bob] hi\n"


def test_read_from_returns_full_lines_with_mid_prefix(tmp_path: Path) -> None:
    """read_from is unchanged — it returns whatever was written, including the MID prefix."""
    inbox = InboxLog(tmp_path)
    inbox.append("alice", "msg-1", "2026-04-30T00:00:00Z [bob] one")
    inbox.append("alice", "msg-2", "2026-04-30T00:00:01Z [bob] two")
    lines, offset = inbox.read_from("alice", 0)
    assert lines == [
        "msg-1\t2026-04-30T00:00:00Z [bob] one",
        "msg-2\t2026-04-30T00:00:01Z [bob] two",
    ]
    assert offset > 0
