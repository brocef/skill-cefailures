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


@pytest.mark.asyncio
async def test_follow_prints_push_message_mid_stream(sock_path, tmp_path):
    """Messages sent after follow starts are pushed and printed."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T")
        cid = r["conversation_id"]
        # Bob must be a member to receive pushes
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--idle-timeout", "2",
            "--timeout", "10",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Give follow time to connect + drain (empty) + start listening.
        await asyncio.sleep(0.3)
        await alice.send_message(cid, "live message")
        await asyncio.sleep(0.3)
        await alice.close()

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        assert "[alice] live message" in lines
        assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_follow_count_exits_after_n_messages(sock_path, tmp_path):
    """--count 1 exits after one new message (history messages do not count)."""
    server = BrokerServer(storage_dir=tmp_path / "convs")
    srv = await start_server(server, sock_path)
    try:
        alice = BrokerClient("alice", sock_path)
        await alice.connect()
        r = await alice.create_conversation("T", content="pre-existing")
        cid = r["conversation_id"]
        bob = BrokerClient("bob", sock_path)
        await bob.connect()
        await bob.join_conversation(cid)
        await bob.close()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, BROKER_CLI, "follow",
            "--identity", "bob",
            "--socket", sock_path,
            "--count", "1",
            "--idle-timeout", "10",
            "--timeout", "20",
            cid,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(0.3)
        await alice.send_message(cid, "msg-1")
        await alice.send_message(cid, "msg-2")  # should be ignored — count already reached
        await alice.close()

        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8.0)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        # History backlog is always printed regardless of count.
        assert "[alice] pre-existing" in lines
        # Exactly one push message is printed.
        push_lines = [l for l in lines if l == "[alice] msg-1" or l == "[alice] msg-2"]
        assert push_lines == ["[alice] msg-1"]
    finally:
        srv.close()
        await srv.wait_closed()
