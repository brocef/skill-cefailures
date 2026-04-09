#!/usr/bin/env python3
"""Async client for the broker socket server."""

import asyncio
import json
import secrets


class BrokerClient:
    """Connects to the broker socket server and provides an async API."""

    def __init__(self, identity: str, sock_path: str) -> None:
        self.identity = identity
        self.sock_path = sock_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._push_buffer: dict[str, list[dict]] = {}  # conversation_id -> list of push messages
        self._listener_task: asyncio.Task | None = None
        self.on_push: asyncio.Queue[dict] | None = None  # optional queue for real-time push notifications

    async def connect(self) -> None:
        """Connect to the broker socket server."""
        self._reader, self._writer = await asyncio.open_unix_connection(self.sock_path)
        self._listener_task = asyncio.create_task(self._listen())
        await self._request({"type": "connect", "identity": self.identity})

    async def close(self) -> None:
        """Close the connection."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def _request(self, msg: dict) -> dict:
        """Send a request and wait for the correlated response."""
        req_id = f"req-{secrets.token_hex(3)}"
        msg["id"] = req_id
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        self._writer.write(json.dumps(msg).encode() + b"\n")
        await self._writer.drain()
        result = await asyncio.wait_for(future, timeout=5.0)
        if result["type"] == "error":
            raise ValueError(result["message"])
        return result.get("data", {})

    async def _listen(self) -> None:
        """Background task that reads messages from the server."""
        try:
            while True:
                line = await self._reader.readline()
                if not line:
                    break
                msg = json.loads(line.decode())
                if msg["type"] in ("response", "error") and "id" in msg:
                    future = self._pending.pop(msg["id"], None)
                    if future and not future.done():
                        future.set_result(msg)
                else:
                    # Push message (message or system event)
                    cid = msg.get("conversation_id", "")
                    self._push_buffer.setdefault(cid, []).append(msg)
                    if self.on_push:
                        await self.on_push.put(msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    def get_new_messages(self, conversation_id: str) -> list[dict]:
        """Return and clear buffered push messages for a conversation."""
        return self._push_buffer.pop(conversation_id, [])

    async def create_conversation(self, topic: str, content: str | None = None) -> dict:
        """Create a new conversation."""
        msg = {"type": "create_conversation", "topic": topic}
        if content:
            msg["content"] = content
        return await self._request(msg)

    async def send_message(self, conversation_id: str, content: str) -> dict:
        """Send a message to a conversation."""
        return await self._request({
            "type": "send_message", "conversation_id": conversation_id, "content": content,
        })

    async def join_conversation(self, conversation_id: str) -> dict:
        """Join a conversation."""
        return await self._request({
            "type": "join_conversation", "conversation_id": conversation_id,
        })

    async def leave_conversation(self, conversation_id: str) -> dict:
        """Leave a conversation."""
        return await self._request({
            "type": "leave_conversation", "conversation_id": conversation_id,
        })

    async def history(self, conversation_id: str) -> dict:
        """Get conversation history (catch-up after reconnect)."""
        return await self._request({
            "type": "history", "conversation_id": conversation_id,
        })

    async def list_conversations(self, status: str | None = None) -> dict:
        """List all conversations."""
        msg = {"type": "list_conversations"}
        if status:
            msg["status"] = status
        return await self._request(msg)

    async def list_members(self, conversation_id: str) -> dict:
        """List members of a conversation."""
        return await self._request({
            "type": "list_members", "conversation_id": conversation_id,
        })

    async def close_conversation(self, conversation_id: str) -> dict:
        """Close a conversation."""
        return await self._request({
            "type": "close_conversation", "conversation_id": conversation_id,
        })
