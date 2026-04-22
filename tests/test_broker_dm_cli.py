import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CLI = [sys.executable, str(SCRIPTS / "broker_cli.py")]


@pytest.fixture
def broker(tmp_path: Path):
    """Start a broker server against tmp_path and yield a dict of paths + env.

    Uses /tmp for the socket to avoid macOS AF_UNIX path-length limits.
    """
    import uuid
    sock = Path(f"/tmp/broker_dm_cli_{uuid.uuid4().hex[:8]}.sock")
    storage = tmp_path / "conversations"
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_STORAGE": str(storage),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    proc = subprocess.Popen(CLI + ["server"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        proc.terminate()
        raise RuntimeError("broker server did not start")
    yield {"env": env, "tmp": tmp_path, "sock": sock}
    proc.terminate()
    proc.wait(timeout=3)
    if sock.exists():
        sock.unlink()


def test_send_dm_writes_to_recipient_inbox(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "hello bob"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    inbox = broker["tmp"] / "inbox" / "bob.log"
    assert inbox.exists(), f"inbox not created at {inbox}. Stderr: {result.stderr}"
    content = inbox.read_text()
    assert "[alice]" in content
    assert content.strip().endswith("hello bob")


def test_send_dm_multi_recipient(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "group ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (broker["tmp"] / "inbox" / "bob.log").exists()
    assert (broker["tmp"] / "inbox" / "carol.log").exists()


def test_broadcast_fans_out(broker) -> None:
    env = broker["env"]
    # Register alice and bob by each sending a DM to the other.
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "seed"], env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "bob", "--to", "alice", "seed"], env=env, capture_output=True, text=True)
    # Broadcast from alice.
    result = subprocess.run(CLI + ["broadcast", "--identity", "alice", "announcement"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    bob_inbox = (broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "→ BROADCAST" in alice_inbox
    assert "→ BROADCAST" in bob_inbox


def test_reply_all_cli(broker) -> None:
    env = broker["env"]
    sent = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "kickoff"],
        env=env, capture_output=True, text=True,
    )
    message_id = sent.stdout.strip()
    assert sent.returncode == 0 and message_id.startswith("msg-")

    result = subprocess.run(
        CLI + ["reply-all", "--identity", "bob", "--to-message", message_id, "responding"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    carol_inbox = (broker["tmp"] / "inbox" / "carol.log").read_text()
    bob_inbox_path = broker["tmp"] / "inbox" / "bob.log"
    bob_inbox = bob_inbox_path.read_text() if bob_inbox_path.exists() else ""
    assert "responding" in alice_inbox
    assert "responding" in carol_inbox
    assert "responding" not in bob_inbox  # no self-echo


def test_history_cli(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "one"], env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "two"], env=env, capture_output=True, text=True)
    result = subprocess.run(CLI + ["history", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("one")
    assert lines[1].endswith("two")


def test_history_cli_sent_flag(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "sent one"], env=env, capture_output=True, text=True)
    result = subprocess.run(CLI + ["history", "--identity", "alice", "--sent"], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert "sent one" in result.stdout


def test_read_cli_inbox_mode(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "msg1"], env=env, capture_output=True, text=True)
    first = subprocess.run(CLI + ["read", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert "msg1" in first.stdout
    second = subprocess.run(CLI + ["read", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert second.stdout.strip() == ""


def test_whoami_prints_derived_identity(tmp_path: Path) -> None:
    import json as _json
    (tmp_path / "package.json").write_text(_json.dumps({"name": "test-pkg"}))
    result = subprocess.run(
        CLI + ["whoami"],
        cwd=tmp_path,
        env={"PATH": Path(sys.executable).parent.as_posix()},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "test-pkg" in result.stdout
    assert str(tmp_path) in result.stdout


def test_create_emits_deprecation_warning(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["create", "--identity", "alice", "test-room"],
        env=env, capture_output=True, text=True,
    )
    # Should succeed (returncode 0) but emit a deprecation warning to stderr.
    assert result.returncode == 0, result.stderr
    assert "deprecat" in result.stderr.lower()


def test_join_emits_deprecation_warning(broker) -> None:
    env = broker["env"]
    # Create a room first (itself will warn).
    created = subprocess.run(
        CLI + ["create", "--identity", "alice", "room"],
        env=env, capture_output=True, text=True,
    )
    import json as _json
    conv_id = _json.loads(created.stdout)["conversation_id"]
    result = subprocess.run(
        CLI + ["join", "--identity", "bob", conv_id],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "deprecat" in result.stderr.lower()


def test_leave_emits_deprecation_warning(broker) -> None:
    env = broker["env"]
    created = subprocess.run(CLI + ["create", "--identity", "alice", "room"], env=env, capture_output=True, text=True)
    import json as _json
    conv_id = _json.loads(created.stdout)["conversation_id"]
    subprocess.run(CLI + ["join", "--identity", "bob", conv_id], env=env, capture_output=True, text=True)
    result = subprocess.run(CLI + ["leave", "--identity", "bob", conv_id], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "deprecat" in result.stderr.lower()


def test_follow_tails_inbox_file(broker) -> None:
    env = broker["env"]
    # Pre-populate one message so follow has something to drain.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "backlog msg"],
        env=env, capture_output=True, text=True,
    )
    # Start follow in background. Short idle-timeout so it exits quickly.
    follow = subprocess.Popen(
        CLI + ["follow", "--identity", "bob", "--idle-timeout", "2"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)
    # Send a live message while follow is running.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "live msg"],
        env=env, capture_output=True, text=True,
    )
    stdout, stderr = follow.communicate(timeout=5)
    assert "backlog msg" in stdout, stderr
    assert "live msg" in stdout, stderr
