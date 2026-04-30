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
async def test_socket_connect_and_send_dm(storage_dir, sock_path):
    """Client can connect via socket and send a DM."""
    server = BrokerServer(root_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        reader, writer = await _connect_client(sock_path)

        await _send(writer, {"id": "r1", "type": "connect", "identity": "alice"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r1"

        await _send(writer, {"id": "r2", "type": "send_dm", "to": ["bob"], "content": "hi"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r2"
        assert "message_id" in resp["data"]

        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_dm_pushes_to_recipient(storage_dir, sock_path):
    """A DM sent over the socket pushes inbox_message to the connected recipient."""
    server = BrokerServer(root_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        r1, w1 = await _connect_client(sock_path)
        r2, w2 = await _connect_client(sock_path)

        await _send(w1, {"id": "r1", "type": "connect", "identity": "alice"})
        await _recv(r1)
        await _send(w2, {"id": "r2", "type": "connect", "identity": "bob"})
        await _recv(r2)

        await _send(w1, {"id": "r3", "type": "send_dm", "to": ["bob"], "content": "Hello bob"})
        await _recv(r1)  # send response

        pushed = await _recv(r2)
        assert pushed["type"] == "inbox_message"
        assert "Hello bob" in pushed["line"]

        w1.close()
        w2.close()
        await w1.wait_closed()
        await w2.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_reserved_identity_without_token_returns_error(storage_dir, sock_path):
    """Connecting as a reserved identity without a token returns a clean error response."""
    server = BrokerServer(root_dir=storage_dir)
    srv = await start_server(server, sock_path)
    try:
        reader, writer = await _connect_client(sock_path)
        await _send(writer, {"id": "r1", "type": "connect", "identity": "@orchestrator/test"})
        resp = await _recv(reader)
        assert resp["type"] == "error"
        assert resp["id"] == "r1"
        assert "reserved" in resp["message"].lower()
        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_reserved_identity_with_valid_token_connects(storage_dir, sock_path):
    """Connecting as a reserved identity with a matching token succeeds."""
    tokens_dir = storage_dir / "tokens"
    tokens_dir.mkdir(parents=True)
    (tokens_dir / "@orchestrator_test.token").write_text("secret-value\n")

    server = BrokerServer(root_dir=storage_dir)
    srv = await start_server(server, sock_path)
    try:
        reader, writer = await _connect_client(sock_path)
        await _send(writer, {
            "id": "r1", "type": "connect",
            "identity": "@orchestrator/test", "token": "secret-value",
        })
        resp = await _recv(reader)
        assert resp["type"] == "response"
        assert resp["id"] == "r1"

        await _send(writer, {"id": "r2", "type": "list_clients"})
        resp = await _recv(reader)
        assert resp["type"] == "response"
        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()


@pytest.mark.asyncio
async def test_socket_reserved_identity_with_wrong_token_returns_error(storage_dir, sock_path):
    """Wrong token for a reserved identity returns a clean error response."""
    tokens_dir = storage_dir / "tokens"
    tokens_dir.mkdir(parents=True)
    (tokens_dir / "@orchestrator_test.token").write_text("real-token\n")

    server = BrokerServer(root_dir=storage_dir)
    srv = await start_server(server, sock_path)
    try:
        reader, writer = await _connect_client(sock_path)
        await _send(writer, {
            "id": "r1", "type": "connect",
            "identity": "@orchestrator/test", "token": "wrong",
        })
        resp = await _recv(reader)
        assert resp["type"] == "error"
        assert "reserved" in resp["message"].lower()
        writer.close()
        await writer.wait_closed()
    finally:
        srv.close()
        await srv.wait_closed()
