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
async def test_client_connect_and_create(tmp_path, sock_path):
    """BrokerClient can connect and create a conversation."""
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path)
        await client.connect()

        result = await client.create_conversation("Test topic")
        assert "conversation_id" in result
        assert result["topic"] == "Test topic"

        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_send_and_receive(tmp_path, sock_path):
    """Two BrokerClients can send and receive messages."""
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        result = await alice.create_conversation("Test")
        cid = result["conversation_id"]
        await bob.join_conversation(cid)

        await alice.send_message(cid, "Hello bob")

        # Give a moment for the push to arrive
        await asyncio.sleep(0.05)

        # Bob should have the message in his buffer
        messages = bob.get_new_messages(cid)
        assert len(messages) >= 1
        content_msgs = [m for m in messages if m.get("message", {}).get("sender") != "system"]
        assert any(m["message"]["content"] == "Hello bob" for m in content_msgs if "message" in m)

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_list_conversations(tmp_path, sock_path):
    """BrokerClient can list conversations."""
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path)
        await client.connect()
        await client.create_conversation("Topic A")
        await client.create_conversation("Topic B")

        result = await client.list_conversations()
        assert len(result["conversations"]) == 2

        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_client_list_members(tmp_path, sock_path):
    """BrokerClient can list conversation members."""
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        result = await alice.create_conversation("Test")
        cid = result["conversation_id"]
        await bob.join_conversation(cid)

        members = await alice.list_members(cid)
        assert sorted(members["members"]) == ["alice", "bob"]

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()
