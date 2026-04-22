"""End-to-end: a multi-agent DM scenario running against a real broker server."""

import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CLI = [sys.executable, str(SCRIPTS / "broker_cli.py")]


@pytest.fixture
def live_broker(tmp_path: Path):
    sock = Path(f"/tmp/broker_dm_e2e_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_STORAGE": str(tmp_path / "conversations"),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    proc = subprocess.Popen(
        CLI + ["server"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        proc.terminate()
        raise RuntimeError("server failed to start")
    yield {"env": env, "tmp": tmp_path}
    proc.terminate()
    proc.wait(timeout=3)
    if sock.exists():
        sock.unlink()


def test_multi_party_dm_with_reply_all(live_broker) -> None:
    """Alice DMs [bob, carol]; bob replies-all; carol follows and sees both messages."""
    env = live_broker["env"]
    def run(*args):
        return subprocess.run(CLI + list(args), env=env, capture_output=True, text=True, timeout=10)

    # Kickoff.
    sent = run("send", "--identity", "alice", "--to", "bob,carol", "kickoff message")
    assert sent.returncode == 0, sent.stderr
    kickoff_id = sent.stdout.strip()
    assert kickoff_id.startswith("msg-")

    # Carol starts a follow with a short idle-timeout.
    follow = subprocess.Popen(
        CLI + ["follow", "--identity", "carol", "--idle-timeout", "2"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)

    # Bob replies-all.
    reply = run("reply-all", "--identity", "bob", "--to-message", kickoff_id, "replying to all")
    assert reply.returncode == 0, reply.stderr

    stdout, stderr = follow.communicate(timeout=5)
    assert "kickoff message" in stdout, f"stdout={stdout!r} stderr={stderr!r}"
    assert "replying to all" in stdout, f"stdout={stdout!r} stderr={stderr!r}"
    # Bob should NOT see his own reply-all in his inbox (no self-echo).
    bob_inbox = (live_broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "replying to all" not in bob_inbox
