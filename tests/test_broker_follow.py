"""Tests for `broker follow` — push-based message consumer."""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.fixture
def sock_path():
    """Unix socket path under /tmp to avoid macOS 104-char limit."""
    fd, path = tempfile.mkstemp(prefix="broker_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


BROKER_CLI = str(Path(__file__).parent.parent / "scripts" / "broker_cli.py")


def test_follow_subcommand_parses_args():
    """Parser accepts all documented flags without error."""
    result = subprocess.run(
        [sys.executable, BROKER_CLI, "follow", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--identity" in result.stdout
    assert "--idle-timeout" in result.stdout
    assert "--timeout" in result.stdout
    assert "--count" in result.stdout
    assert "--include-system" in result.stdout
    assert "--format" in result.stdout


@pytest.mark.asyncio
async def test_follow_drains_backlog_then_exits_on_idle(sock_path, tmp_path):
    """Follow prints history then exits when idle-timeout elapses."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T", content="first message")
        cid = r["conversation_id"]
        await alice.send_message(cid, "second message")
        await alice.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--idle-timeout", "1",
            "--timeout", "10",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[alice] first message" in lines
        assert "[alice] second message" in lines
        assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    finally:
        srv.close()
        await srv.wait_closed()
