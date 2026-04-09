#!/usr/bin/env python3
"""MCP server that enables two Claude Code instances to hold structured conversations."""

import argparse
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP


class ConversationStore:
    """File-backed conversation storage with per-identity cursors."""

    def __init__(self, identity: str, storage_dir: Path) -> None:
        self.identity = identity
        self.storage_dir = storage_dir

    def _generate_id(self) -> str:
        """Generate a short random hex ID."""
        return secrets.token_hex(3)

    def _message_id(self) -> str:
        """Generate a message ID."""
        return f"msg-{self._generate_id()}"

    def _resolve_path(self, conversation_id: str) -> Path:
        """Resolve a conversation file path, rejecting path traversal."""
        path = (self.storage_dir / f"{conversation_id}.json").resolve()
        if not path.is_relative_to(self.storage_dir.resolve()):
            raise ValueError(f"Invalid conversation ID: '{conversation_id}'")
        return path

    def _load(self, conversation_id: str) -> dict:
        """Load a conversation from disk."""
        path = self._resolve_path(conversation_id)
        if not path.exists():
            raise ValueError(f"Conversation '{conversation_id}' not found")
        return json.loads(path.read_text())

    def _save(self, conversation: dict) -> None:
        """Write a conversation to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        path = self._resolve_path(conversation["id"])
        path.write_text(json.dumps(conversation, indent=2))

    def create_conversation(self, topic: str) -> dict:
        """Start a new conversation."""
        conv_id = self._generate_id()
        conversation = {
            "id": conv_id,
            "topic": topic,
            "status": "open",
            "createdBy": self.identity,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "cursors": {self.identity: 0},
        }
        self._save(conversation)
        return {
            "conversation_id": conv_id,
            "topic": topic,
            "created_by": self.identity,
        }

    def send_message(self, conversation_id: str, content: str) -> dict:
        """Append a message to a conversation."""
        conversation = self._load(conversation_id)
        if conversation["status"] == "closed":
            raise ValueError(f"Conversation '{conversation_id}' is closed")
        msg_id = self._message_id()
        message = {
            "id": msg_id,
            "sender": self.identity,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        conversation["messages"].append(message)
        self._save(conversation)
        return {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "sender": self.identity,
        }

    def read_new_messages(self, conversation_id: str) -> dict:
        """Read messages not yet seen by the calling identity."""
        conversation = self._load(conversation_id)
        cursor = conversation["cursors"].get(self.identity, 0)
        messages = conversation["messages"][cursor:]
        # Advance cursor
        conversation["cursors"][self.identity] = len(conversation["messages"])
        self._save(conversation)
        # Filter out the caller's own messages
        other_messages = [m for m in messages if m["sender"] != self.identity]
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": m["id"],
                    "sender": m["sender"],
                    "content": m["content"],
                    "timestamp": m["timestamp"],
                }
                for m in other_messages
            ],
            "remaining_unread": 0,
        }

    def list_conversations(self, status: str | None = None) -> dict:
        """List all conversations, optionally filtered by status."""
        conversations = []
        if not self.storage_dir.exists():
            return {"conversations": []}
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            if status and data["status"] != status:
                continue
            cursor = data["cursors"].get(self.identity, 0)
            unread = [
                m for m in data["messages"][cursor:]
                if m["sender"] != self.identity
            ]
            conversations.append({
                "id": data["id"],
                "topic": data["topic"],
                "status": data["status"],
                "created_by": data["createdBy"],
                "message_count": len(data["messages"]),
                "unread_count": len(unread),
            })
        return {"conversations": conversations}

    def close_conversation(self, conversation_id: str) -> dict:
        """Mark a conversation as closed (read-only)."""
        conversation = self._load(conversation_id)
        conversation["status"] = "closed"
        self._save(conversation)
        return {
            "conversation_id": conversation_id,
            "status": "closed",
        }


mcp = FastMCP("mcp-broker")

store: ConversationStore


@mcp.tool()
def create_conversation(topic: str) -> dict:
    """Start a new conversation with the given topic."""
    return store.create_conversation(topic)


@mcp.tool()
def send_message(conversation_id: str, content: str) -> dict:
    """Append a message to an existing conversation."""
    return store.send_message(conversation_id, content)


@mcp.tool()
def read_new_messages(conversation_id: str) -> dict:
    """Read messages not yet seen by the calling identity."""
    return store.read_new_messages(conversation_id)


@mcp.tool()
def list_conversations(status: str | None = None) -> dict:
    """List all conversations, optionally filtered by status ('open' or 'closed')."""
    return store.list_conversations(status)


@mcp.tool()
def close_conversation(conversation_id: str) -> dict:
    """Mark a conversation as closed. Closed conversations are read-only."""
    return store.close_conversation(conversation_id)


def main() -> None:
    """Parse CLI args and start the MCP server."""
    global store
    parser = argparse.ArgumentParser(description="MCP message broker server")
    parser.add_argument("--identity", required=True, help="Identity for this connection (e.g. 'core')")
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=Path.home() / ".mcp-broker" / "conversations",
        help="Directory for conversation files (default: ~/.mcp-broker/conversations)",
    )
    args = parser.parse_args()
    store = ConversationStore(identity=args.identity, storage_dir=args.storage_dir)
    mcp.run()


if __name__ == "__main__":
    main()
