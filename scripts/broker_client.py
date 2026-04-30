#!/usr/bin/env python3
"""Async client for the broker socket server."""

import asyncio
import json
import secrets


class BrokerClient:
    """Connects to the broker socket server and provides an async DM API."""

    def __init__(self, identity: str, sock_path: str, token: str | None = None) -> None:
        self.identity = identity
        self.sock_path = sock_path
        self.token = token
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._listener_task: asyncio.Task | None = None
        self.on_push: asyncio.Queue[dict] | None = None  # optional queue for live inbox_message pushes

    async def connect(self) -> None:
        """Connect to the broker socket server."""
        self._reader, self._writer = await asyncio.open_unix_connection(self.sock_path)
        self._listener_task = asyncio.create_task(self._listen())
        msg: dict = {"type": "connect", "identity": self.identity}
        if self.token is not None:
            msg["token"] = self.token
        await self._request(msg)

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
                elif self.on_push is not None:
                    await self.on_push.put(msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    async def send_dm(self, to: list[str], content: str) -> dict:
        """Send a direct message to one or more recipients."""
        return await self._request({"type": "send_dm", "to": to, "content": content})

    async def broadcast(self, content: str) -> dict:
        """Broadcast to every registered identity."""
        return await self._request({"type": "send_broadcast", "content": content})

    async def reply_all(self, to_message: str, content: str) -> dict:
        """Reply to everyone on a prior DM (excluding self)."""
        return await self._request({
            "type": "reply_all", "to_message": to_message, "content": content,
        })

    async def history_inbox(
        self, *, sender: str | None = None, since: str | None = None, sent: bool = False,
    ) -> dict:
        """Read inbox (or outbox with `sent=True`) without advancing the cursor."""
        msg: dict = {"type": "history_inbox"}
        if sender: msg["from"] = sender
        if since: msg["since"] = since
        if sent: msg["sent"] = True
        return await self._request(msg)

    async def read_inbox(self) -> dict:
        """Read new inbox lines since the last read-cursor; advances the cursor."""
        return await self._request({"type": "read_inbox"})

    async def list_clients(self) -> dict:
        """List identities currently holding a live connection to the server."""
        return await self._request({"type": "list_clients"})
