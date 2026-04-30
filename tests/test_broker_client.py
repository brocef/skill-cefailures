import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.fixture
def sock_path():
    """Create a short socket path to avoid AF_UNIX length limits on macOS."""
    fd, path = tempfile.mkstemp(prefix="broker_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)  # we just need the path, not the file
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_client_connect_and_disconnect(tmp_path, sock_path):
    """BrokerClient can connect and cleanly disconnect."""
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path)
        await client.connect()
        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_send_dm_round_trip(tmp_path, sock_path):
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)

    alice = BrokerClient("alice", sock_path); await alice.connect()
    bob = BrokerClient("bob", sock_path); await bob.connect()
    try:
        result = await alice.send_dm(["bob"], "hello bob")
        assert "message_id" in result
    finally:
        await alice.close()
        await bob.close()
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_broadcast_round_trip(tmp_path, sock_path):
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)

    alice = BrokerClient("alice", sock_path); await alice.connect()
    bob = BrokerClient("bob", sock_path); await bob.connect()
    try:
        await alice.send_dm(["bob"], "seed")
        result = await alice.broadcast("to all")
        assert result["recipient_count"] >= 2
    finally:
        await alice.close(); await bob.close()
        srv.close(); await srv.wait_closed()


@pytest.mark.asyncio
async def test_reply_all_round_trip(tmp_path, sock_path):
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)

    alice = BrokerClient("alice", sock_path); await alice.connect()
    bob = BrokerClient("bob", sock_path); await bob.connect()
    carol = BrokerClient("carol", sock_path); await carol.connect()
    try:
        sent = await alice.send_dm(["bob", "carol"], "kickoff")
        reply = await bob.reply_all(sent["message_id"], "responding")
        assert set(reply["recipients"]) == {"alice", "carol"}
    finally:
        for c in (alice, bob, carol): await c.close()
        srv.close(); await srv.wait_closed()


@pytest.mark.asyncio
async def test_history_inbox_and_read_inbox(tmp_path, sock_path):
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)

    alice = BrokerClient("alice", sock_path); await alice.connect()
    bob = BrokerClient("bob", sock_path); await bob.connect()
    try:
        await alice.send_dm(["bob"], "one")
        await alice.send_dm(["bob"], "two")
        hist = await bob.history_inbox()
        assert len(hist["lines"]) == 2
        first = await bob.read_inbox()
        assert len(first["lines"]) == 2
        second = await bob.read_inbox()
        assert second["lines"] == []
    finally:
        await alice.close(); await bob.close()
        srv.close(); await srv.wait_closed()
