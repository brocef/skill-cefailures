import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path


@pytest.fixture
def sock_path():
    """Create a short socket path to avoid AF_UNIX length limits on macOS."""
    fd, path = tempfile.mkstemp(suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


async def _connect_client(sock_path: str) -> tuple:
    """Connect a client to the socket and return (reader, writer)."""
    reader, writer = await asyncio.open_unix_connection(sock_path)
    return reader, writer


async def _send(writer: asyncio.StreamWriter, msg: dict) -> None:
    """Send a line-delimited JSON message."""
    writer.write(json.dumps(msg).encode() + b"\n")
    await writer.drain()


async def _recv(reader: asyncio.StreamReader) -> dict:
    """Read one line-delimited JSON message."""
    line = await asyncio.wait_for(reader.readline(), timeout=2.0)
    return json.loads(line)


@pytest.mark.asyncio
async def test_socket_connect_and_create(storage_dir, sock_path):
    """Client can connect via socket and create a conversation."""
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        reader, writer = await _connect_client(sock_path)

        await _send(writer, {"id": "r1", "type": "connect", "identity": "alice"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r1"

        await _send(writer, {"id": "r2", "type": "create_conversation", "topic": "Test"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r2"
        assert "conversation_id" in resp["data"]

        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_message_push(storage_dir, sock_path):
    """Messages are pushed to other connected members via socket."""
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        r1, w1 = await _connect_client(sock_path)
        r2, w2 = await _connect_client(sock_path)

        await _send(w1, {"id": "r1", "type": "connect", "identity": "alice"})
        await _recv(r1)
        await _send(w2, {"id": "r2", "type": "connect", "identity": "bob"})
        await _recv(r2)

        await _send(w1, {"id": "r3", "type": "create_conversation", "topic": "Test"})
        resp = await _recv(r1)
        cid = resp["data"]["conversation_id"]

        await _send(w2, {"id": "r4", "type": "join_conversation", "conversation_id": cid})
        await _recv(r2)  # join response
        # alice gets bob's join system message
        sys_msg = await _recv(r1)
        assert sys_msg["type"] == "system"

        await _send(w1, {"id": "r5", "type": "send_message", "conversation_id": cid, "content": "Hello bob"})
        await _recv(r1)  # send response

        # Bob should receive the pushed message
        pushed = await _recv(r2)
        assert pushed["type"] == "message"
        assert pushed["message"]["content"] == "Hello bob"

        w1.close()
        w2.close()
        await w1.wait_closed()
        await w2.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()
