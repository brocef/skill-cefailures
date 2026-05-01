#!/usr/bin/env python3
"""Broker server: identity registry, store-and-forward inbox, DM/broadcast/reply-all routing."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from broker_constants import BROADCAST
from broker_format import format_message, parse_message, split_mid_prefix
from broker_storage import InboxLog, OutboxLog, CursorStore, IdentityRegistry


class BrokerServer:
    """Central broker that routes DMs, broadcasts, and reply-all between identities."""

    def __init__(self, root_dir: Path, audit_hook: Callable[[str], None] | None = None) -> None:
        self.root_dir = root_dir
        self.clients: dict[str, Callable] = {}
        self.followers: dict[str, dict] = {}
        self.audit_hook = audit_hook  # called once per routed message with the formatted line
        self.inbox_log = InboxLog(root_dir / "inbox")
        self.outbox_log = OutboxLog(root_dir / "outbox")
        self.cursors = CursorStore(root_dir / "cursors")
        self.registry = IdentityRegistry(root_dir / "identities.json")

    def _generate_id(self) -> str:
        # 6 hex chars + "msg-" prefix = 10-char message ID. If you change this,
        # update MID_COLUMN_WIDTH in broker_cli.py to match.
        return secrets.token_hex(3)

    def _message_id(self) -> str:
        return f"msg-{self._generate_id()}"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def connect(self, identity: str, send: Callable, mode: str = "oneshot", token: str | None = None) -> None:
        """Register a client connection.

        BROADCAST is reserved as the fan-out pseudo-recipient and cannot be claimed
        as an identity. All other identities — including @orchestrator/<scope> and
        `human` — are name-reservations only, not auth-gated. The agent-side authority
        hierarchy (see skills/broker/docs/authority.md) gives `user` and orchestrator
        identities high trust by convention, but the broker performs no authentication.

        `mode="follow"` also registers the identity in `self.followers` (presence registry).
        `mode="oneshot"` only updates `self.clients`.
        """
        if identity == BROADCAST:
            raise ValueError("BROADCAST is reserved and cannot be claimed as an identity.")
        self.clients[identity] = send
        if mode == "follow":
            self.followers[identity] = {"since": self._timestamp()}
        self.registry.touch(identity, now=self._timestamp(), wrote=False)

    def disconnect(self, identity: str) -> None:
        """Remove the client's push callback. Inbox state is unaffected."""
        self.clients.pop(identity, None)
        self.followers.pop(identity, None)

    def handle_request(self, identity: str, msg: dict) -> dict:
        """Dispatch a client request and return a response or error."""
        req_id = msg.get("id", "")
        msg_type = msg.get("type", "")

        try:
            handler = {
                "send_dm": self._handle_send_dm,
                "send_broadcast": self._handle_broadcast,
                "reply_all": self._handle_reply_all,
                "history_inbox": self._handle_history_inbox,
                "read_inbox": self._handle_read_inbox,
                "list_clients": self._handle_list_clients,
            }.get(msg_type)

            if not handler:
                return {"type": "error", "id": req_id, "message": f"Unknown request type: {msg_type}"}

            data = handler(identity, msg)
            return {"type": "response", "id": req_id, "data": data}
        except ValueError as e:
            return {"type": "error", "id": req_id, "message": str(e)}

    def _handle_send_dm(self, identity: str, msg: dict) -> dict:
        """Send a direct message to one or more recipients.

        Appends to each recipient's inbox log, appends to the sender's outbox log,
        and pushes `inbox_message` to each online recipient. Rejects BROADCAST in `to`.
        """
        to = msg.get("to") or []
        content = msg.get("content", "")
        if BROADCAST in to:
            raise ValueError("BROADCAST is not a valid recipient; use send_broadcast.")
        if not to:
            raise ValueError("send_dm requires at least one recipient in `to`.")

        message_id = self._message_id()
        timestamp = self._timestamp()
        self._record_dm(message_id, identity, to, timestamp, content, is_broadcast=False)

        for recipient in to:
            line = format_message(timestamp, identity, to, content, viewer=recipient)
            self.inbox_log.append(recipient, message_id, line)
            if recipient in self.clients and recipient != identity:
                self.clients[recipient]({
                    "type": "inbox_message",
                    "message_id": message_id,
                    "recipient": recipient,
                    "line": line,
                })

        sender_line = format_message(timestamp, identity, to, content, viewer=identity)
        self.outbox_log.append(identity, message_id, sender_line)

        if self.audit_hook is not None:
            self.audit_hook(sender_line)

        self.registry.touch(identity, now=timestamp, wrote=True)
        return {"message_id": message_id, "recipients": list(to)}

    def _handle_broadcast(self, identity: str, msg: dict) -> dict:
        """Fan out to every registered identity's inbox."""
        content = msg.get("content", "")
        message_id = self._message_id()
        timestamp = self._timestamp()
        recipients = [BROADCAST]
        self._record_dm(message_id, identity, recipients, timestamp, content, is_broadcast=True)

        for dest in self.registry.all():
            line = format_message(timestamp, identity, recipients, content, viewer=dest)
            self.inbox_log.append(dest, message_id, line)
            if dest in self.clients and dest != identity:
                self.clients[dest]({
                    "type": "inbox_message",
                    "message_id": message_id,
                    "recipient": dest,
                    "line": line,
                })

        sender_line = format_message(timestamp, identity, recipients, content, viewer=identity)
        self.outbox_log.append(identity, message_id, sender_line)

        if self.audit_hook is not None:
            self.audit_hook(sender_line)

        self.registry.touch(identity, now=timestamp, wrote=True)
        return {"message_id": message_id, "recipient_count": len(self.registry.all())}

    def _load_message_record(self, message_id: str) -> dict | None:
        path = self.root_dir / "messages" / f"{message_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _handle_reply_all(self, identity: str, msg: dict) -> dict:
        """Reply to everyone on a prior DM thread (excluding self).

        Rejects if the target message was a broadcast.
        """
        record = self._load_message_record(msg["to_message"])
        if record is None:
            raise ValueError(f"Message '{msg['to_message']}' not found")
        if record["is_broadcast"]:
            raise ValueError("Cannot reply-all to a broadcast; use send_dm instead.")

        recipients = [record["sender"]] + list(record["to"])
        recipients = [r for r in recipients if r != identity]
        seen: set[str] = set()
        ordered: list[str] = []
        for r in recipients:
            if r not in seen:
                seen.add(r)
                ordered.append(r)
        if not ordered:
            raise ValueError("reply-all yielded an empty recipient set (you were the only party).")

        return self._handle_send_dm(identity, {
            "type": "send_dm",
            "id": msg.get("id", ""),
            "to": ordered,
            "content": msg.get("content", ""),
        })

    def _handle_history_inbox(self, identity: str, msg: dict) -> dict:
        """Read the identity's inbox (or outbox, with `sent=True`) without advancing the cursor.

        Optional filters:
            from: only lines whose sender matches this identity
            since: only lines with timestamp >= this ISO8601 string
        """
        sent = bool(msg.get("sent"))
        if sent:
            lines = self.outbox_log.read_all(identity)
        else:
            lines, _ = self.inbox_log.read_from(identity, 0)

        from_filter = msg.get("from")
        since = msg.get("since")
        if from_filter or since:
            filtered: list[str] = []
            for line in lines:
                try:
                    _, display = split_mid_prefix(line)
                    parsed = parse_message(display, viewer=identity)
                except ValueError:
                    continue
                if from_filter and parsed.sender != from_filter:
                    continue
                if since and parsed.timestamp < since:
                    continue
                filtered.append(line)
            lines = filtered
        self.registry.touch(identity, now=self._timestamp(), wrote=False)
        return {"lines": lines}

    def _handle_read_inbox(self, identity: str, msg: dict) -> dict:
        """Return inbox lines since the identity's last read-cursor; advance the cursor."""
        offset = self.cursors.get(identity)
        lines, new_offset = self.inbox_log.read_from(identity, offset)
        self.cursors.set(identity, new_offset)
        self.registry.touch(identity, now=self._timestamp(), wrote=False)
        return {"lines": lines}

    def _handle_list_clients(self, identity: str, msg: dict) -> dict:
        """Return the identities currently holding a live socket connection.

        This is presence (live push targets), not the registry (everyone the
        broker has ever heard from). Sorted for stable output.
        """
        return {"clients": sorted(self.clients.keys())}

    def _record_dm(
        self,
        message_id: str,
        sender: str,
        to: list[str],
        timestamp: str,
        content: str,
        is_broadcast: bool,
    ) -> None:
        """Store the raw fields needed to answer reply-all queries."""
        messages_dir = self.root_dir / "messages"
        messages_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "id": message_id,
            "sender": sender,
            "to": list(to),
            "timestamp": timestamp,
            "content": content,
            "is_broadcast": is_broadcast,
        }
        (messages_dir / f"{message_id}.json").write_text(json.dumps(record))


async def _handle_client(server: BrokerServer, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Handle a single client connection."""
    identity = None
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            msg = json.loads(line.decode())

            if msg["type"] == "connect":
                req_identity = msg["identity"]
                req_mode = msg.get("mode", "oneshot")
                def send(m, w=writer):
                    w.write(json.dumps(m).encode() + b"\n")
                try:
                    server.connect(req_identity, send, mode=req_mode, token=msg.get("token"))
                except ValueError as exc:
                    error = {"type": "error", "id": msg.get("id", ""), "message": str(exc)}
                    writer.write(json.dumps(error).encode() + b"\n")
                    await writer.drain()
                    break
                identity = req_identity
                response = {"type": "response", "id": msg.get("id", ""), "data": {"status": "connected"}}
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
            else:
                response = server.handle_request(identity, msg)
                writer.write(json.dumps(response).encode() + b"\n")
                await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        if identity:
            server.disconnect(identity)
        writer.close()


async def start_server(server: BrokerServer, sock_path: str) -> asyncio.AbstractServer:
    """Start the Unix domain socket server."""
    Path(sock_path).unlink(missing_ok=True)
    srv = await asyncio.start_unix_server(
        lambda r, w: _handle_client(server, r, w),
        path=sock_path,
    )
    return srv
