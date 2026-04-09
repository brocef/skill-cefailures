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
    """Create a socket path in /tmp to avoid macOS 104-char path length limit."""
    fd, path = tempfile.mkstemp(prefix="broker_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_full_conversation_flow(tmp_path, sock_path):
    """End-to-end: server + two clients, create/join/send/read/leave/close."""
    storage_dir = tmp_path / "convs"
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)

    try:
        alice = BrokerClient(identity="alice", sock_path=sock_path)
        bob = BrokerClient(identity="bob", sock_path=sock_path)
        await alice.connect()
        await bob.connect()

        # Alice creates a conversation with a seed
        result = await alice.create_conversation("Design review", content="Please review the PR")
        cid = result["conversation_id"]

        # Bob joins
        await bob.join_conversation(cid)

        # Bob gets history (should include seed message)
        history = await bob.history(cid)
        contents = [m["content"] for m in history["messages"] if m["sender"] != "system"]
        assert "Please review the PR" in contents

        # Bob sends a message
        await bob.send_message(cid, "LGTM, merging now")
        await asyncio.sleep(0.05)

        # Alice should have received the push
        alice_msgs = alice.get_new_messages(cid)
        pushed_contents = [m["message"]["content"] for m in alice_msgs if m["type"] == "message"]
        assert "LGTM, merging now" in pushed_contents

        # List members
        members = await alice.list_members(cid)
        assert sorted(members["members"]) == ["alice", "bob"]

        # Bob leaves
        await bob.leave_conversation(cid)
        await asyncio.sleep(0.05)

        # Alice should get leave system event
        alice_msgs = alice.get_new_messages(cid)
        leave_events = [m for m in alice_msgs if m["type"] == "system" and m["event"] == "leave"]
        assert any(e["identity"] == "bob" for e in leave_events)

        # Alice closes the conversation
        await alice.close_conversation(cid)

        # Sending to closed fails
        with pytest.raises(ValueError, match="closed"):
            await bob.send_message(cid, "Too late")

        # List shows closed
        convs = await alice.list_conversations(status="closed")
        assert len(convs["conversations"]) == 1

        await alice.close()
        await bob.close()
    finally:
        srv.close()
        await srv.wait_closed()
