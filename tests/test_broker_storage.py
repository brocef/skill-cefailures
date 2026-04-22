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
    assert encode_identity("@proposit/shared") == "@proposit_shared"
    assert encode_identity("Proposit-App/proposit-mobile") == "Proposit-App_proposit-mobile"
    assert encode_identity("plain") == "plain"


def test_inbox_append_reads_back(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "line one")
    log.append("alice", "line two")
    assert log.path_for("alice").read_text() == "line one\nline two\n"


def test_inbox_read_from_offset(tmp_path: Path) -> None:
    log = InboxLog(tmp_path)
    log.append("alice", "one")
    log.append("alice", "two")
    log.append("alice", "three")
    first_line_end = len("one\n")
    lines, new_offset = log.read_from("alice", offset=first_line_end)
    assert lines == ["two", "three"]
    assert new_offset == len("one\ntwo\nthree\n")


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
    log.append("alice", "first sent")
    log.append("alice", "second sent")
    assert log.path_for("alice").read_text() == "first sent\nsecond sent\n"


def test_outbox_read_all(tmp_path: Path) -> None:
    log = OutboxLog(tmp_path)
    log.append("alice", "a")
    log.append("alice", "b")
    assert log.read_all("alice") == ["a", "b"]
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
