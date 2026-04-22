#!/usr/bin/env python3
"""Broker server: in-memory conversation state, membership tracking, message routing."""

import asyncio
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from broker_constants import BROADCAST
from broker_format import format_message
from broker_storage import InboxLog, OutboxLog, CursorStore, IdentityRegistry


class BrokerServer:
    """Central broker that manages conversations, membership, and message routing."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir  # conversations dir (legacy rooms)
        self.conversations: dict[str, dict] = {}
        self.members: dict[str, set[str]] = {}
        self.clients: dict[str, Callable] = {}
        # DM model: inbox/outbox/cursors live as siblings of conversations/.
        root = storage_dir.parent
        self.inbox_log = InboxLog(root / "inbox")
        self.outbox_log = OutboxLog(root / "outbox")
        self.cursors = CursorStore(root / "cursors")
        self.registry = IdentityRegistry(root / "identities.json")
        self._load_from_disk()

    def _generate_id(self) -> str:
        """Generate a short random hex ID."""
        return secrets.token_hex(3)

    def _message_id(self) -> str:
        """Generate a message ID."""
        return f"msg-{self._generate_id()}"

    def _timestamp(self) -> str:
        """Generate an ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _load_from_disk(self) -> None:
        """Load existing conversations from disk into memory."""
        if not self.storage_dir.exists():
            return
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            self.conversations[data["id"]] = data
            self.members.setdefault(data["id"], set())

    def _save_conversation(self, conversation_id: str) -> None:
        """Persist a single conversation to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        conv = self.conversations[conversation_id]
        path = self.storage_dir / f"{conversation_id}.json"
        path.write_text(json.dumps(conv, indent=2))

    def connect(self, identity: str, send: Callable) -> None:
        """Register a client connection."""
        self.clients[identity] = send

    def disconnect(self, identity: str) -> None:
        """Remove the client's push callback. Does not change conversation membership.

        Membership is declarative: it changes only via explicit join / leave / close.
        Disconnecting does not broadcast a leave event — that was a historical bug
        that caused join/leave spam across every send/read cycle.
        """
        self.clients.pop(identity, None)

    def handle_request(self, identity: str, msg: dict) -> dict:
        """Dispatch a client request and return a response or error."""
        req_id = msg.get("id", "")
        msg_type = msg.get("type", "")

        try:
            handler = {
                "create_conversation": self._handle_create,
                "join_conversation": self._handle_join,
                "leave_conversation": self._handle_leave,
                "send_message": self._handle_send,
                "history": self._handle_history,
                "list_conversations": self._handle_list,
                "list_members": self._handle_list_members,
                "close_conversation": self._handle_close,
                "send_dm": self._handle_send_dm,
            }.get(msg_type)

            if not handler:
                return {"type": "error", "id": req_id, "message": f"Unknown request type: {msg_type}"}

            data = handler(identity, msg)
            return {"type": "response", "id": req_id, "data": data}
        except ValueError as e:
            return {"type": "error", "id": req_id, "message": str(e)}

    def _join_member(self, conversation_id: str, identity: str) -> None:
        """Add an identity to a conversation's member set and broadcast join."""
        members = self.members.setdefault(conversation_id, set())
        if identity not in members:
            members.add(identity)
            self._broadcast_system(conversation_id, "join", identity)

    def _broadcast_system(self, conversation_id: str, event: str, identity: str) -> None:
        """Create a system message, persist it, and push to connected members.

        The push payload includes the full persisted message dict (with id) so
        consumers can dedup system events by id the same way as user messages.
        The legacy event/identity fields are preserved for back-compat.
        """
        msg = {
            "id": self._message_id(),
            "sender": "system",
            "content": f"{identity} {event}ed" if event == "join" else f"{identity} left",
            "timestamp": self._timestamp(),
        }
        self.conversations[conversation_id]["messages"].append(msg)
        self._save_conversation(conversation_id)
        push = {
            "type": "system",
            "conversation_id": conversation_id,
            "event": event,
            "identity": identity,
            "message": msg,
        }
        for member in self.members.get(conversation_id, set()):
            if member != identity and member in self.clients:
                self.clients[member](push)

    def _handle_create(self, identity: str, msg: dict) -> dict:
        """Handle create_conversation request."""
        conv_id = self._generate_id()
        conversation = {
            "id": conv_id,
            "topic": msg["topic"],
            "status": "open",
            "createdBy": identity,
            "createdAt": self._timestamp(),
            "messages": [],
            "cursors": {},
        }
        self.conversations[conv_id] = conversation
        self.members[conv_id] = set()
        self._join_member(conv_id, identity)

        if msg.get("content"):
            user_msg = {
                "id": self._message_id(),
                "sender": identity,
                "content": msg["content"],
                "timestamp": self._timestamp(),
            }
            conversation["messages"].append(user_msg)

        self._save_conversation(conv_id)
        return {"conversation_id": conv_id, "topic": msg["topic"], "created_by": identity}

    def _handle_join(self, identity: str, msg: dict) -> dict:
        """Handle join_conversation request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        self._join_member(cid, identity)
        return {"conversation_id": cid, "status": "joined"}

    def _handle_leave(self, identity: str, msg: dict) -> dict:
        """Handle leave_conversation request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        members = self.members.get(cid, set())
        if identity in members:
            members.discard(identity)
            self._broadcast_system(cid, "leave", identity)
        return {"conversation_id": cid, "status": "left"}

    def _handle_send(self, identity: str, msg: dict) -> dict:
        """Handle send_message request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        conv = self.conversations[cid]
        if conv["status"] == "closed":
            raise ValueError(f"Conversation '{cid}' is closed")

        self._join_member(cid, identity)

        user_msg = {
            "id": self._message_id(),
            "sender": identity,
            "content": msg["content"],
            "timestamp": self._timestamp(),
        }
        conv["messages"].append(user_msg)
        self._save_conversation(cid)

        push = {"type": "message", "conversation_id": cid, "message": user_msg}
        for member in self.members.get(cid, set()):
            if member != identity and member in self.clients:
                self.clients[member](push)

        return {"message_id": user_msg["id"], "conversation_id": cid, "sender": identity}

    def _handle_history(self, identity: str, msg: dict) -> dict:
        """Handle history request — returns all messages for catch-up."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        conv = self.conversations[cid]
        cursor = conv["cursors"].get(identity, 0)
        messages = conv["messages"][cursor:]
        conv["cursors"][identity] = len(conv["messages"])
        self._save_conversation(cid)
        return {
            "conversation_id": cid,
            "messages": [
                {"id": m["id"], "sender": m["sender"], "content": m["content"], "timestamp": m["timestamp"]}
                for m in messages
            ],
        }

    def _handle_list(self, identity: str, msg: dict) -> dict:
        """Handle list_conversations request.

        Default: returns only conversations with status='open'. Pass status='all'
        to return everything, or status='open'/'closed' for explicit filtering.
        """
        status_filter = msg.get("status", "open")
        conversations = []
        for conv in self.conversations.values():
            if status_filter != "all" and conv["status"] != status_filter:
                continue
            cursor = conv["cursors"].get(identity, 0)
            non_system = [m for m in conv["messages"] if m["sender"] != "system"]
            unread = [m for m in conv["messages"][cursor:] if m["sender"] not in ("system", identity)]
            conversations.append({
                "id": conv["id"],
                "topic": conv["topic"],
                "status": conv["status"],
                "created_by": conv["createdBy"],
                "message_count": len(non_system),
                "unread_count": len(unread),
            })
        return {"conversations": conversations}

    def _handle_list_members(self, identity: str, msg: dict) -> dict:
        """Handle list_members request."""
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        members = sorted(self.members.get(cid, set()))
        return {"conversation_id": cid, "members": members}

    def _handle_close(self, identity: str, msg: dict) -> dict:
        """Handle close_conversation request.

        Flips the conversation to read-only and pushes a conversation_closed
        event to every connected member except the closer. Followers treat
        the event as an explicit exit signal.
        """
        cid = msg["conversation_id"]
        if cid not in self.conversations:
            raise ValueError(f"Conversation '{cid}' not found")
        self.conversations[cid]["status"] = "closed"
        self._save_conversation(cid)

        push = {"type": "conversation_closed", "conversation_id": cid}
        for member in self.members.get(cid, set()):
            if member != identity and member in self.clients:
                self.clients[member](push)

        return {"conversation_id": cid, "status": "closed"}

    def _handle_send_dm(self, identity: str, msg: dict) -> dict:
        """Handle a direct-message send.

        msg: { type, id, to: [identity, ...], content }
        Rejects if `to` contains BROADCAST (use send_broadcast instead).
        Appends to each recipient's inbox log, appends to sender's outbox log,
        and pushes `inbox_message` to each online recipient.
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
            self.inbox_log.append(recipient, line)
            if recipient in self.clients and recipient != identity:
                self.clients[recipient]({
                    "type": "inbox_message",
                    "message_id": message_id,
                    "recipient": recipient,
                    "line": line,
                })

        sender_line = format_message(timestamp, identity, to, content, viewer=identity)
        self.outbox_log.append(identity, sender_line)

        self.registry.touch(identity, now=timestamp, wrote=True)
        return {"message_id": message_id, "recipients": list(to)}

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
        self.storage_dir.parent.joinpath("messages").mkdir(parents=True, exist_ok=True)
        record = {
            "id": message_id,
            "sender": sender,
            "to": list(to),
            "timestamp": timestamp,
            "content": content,
            "is_broadcast": is_broadcast,
        }
        path = self.storage_dir.parent / "messages" / f"{message_id}.json"
        path.write_text(json.dumps(record))


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
                identity = msg["identity"]
                def send(m, w=writer):
                    w.write(json.dumps(m).encode() + b"\n")
                server.connect(identity, send)
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
