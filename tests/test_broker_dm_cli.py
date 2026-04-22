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
