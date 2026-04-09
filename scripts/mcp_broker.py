#!/usr/bin/env python3
"""MCP server that enables two Claude Code instances to hold structured conversations."""

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


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

    def _load(self, conversation_id: str) -> dict:
        """Load a conversation from disk."""
        path = self.storage_dir / f"{conversation_id}.json"
        if not path.exists():
            raise ValueError(f"Conversation '{conversation_id}' not found")
        return json.loads(path.read_text())

    def _save(self, conversation: dict) -> None:
        """Write a conversation to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        path = self.storage_dir / f"{conversation['id']}.json"
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
        # Advance sender's cursor to include their own message
        conversation["cursors"][self.identity] = len(conversation["messages"])
        self._save(conversation)
        return {
            "message_id": msg_id,
            "conversation_id": conversation_id,
            "sender": self.identity,
        }

    def close_conversation(self, conversation_id: str) -> dict:
        """Mark a conversation as closed (read-only)."""
        conversation = self._load(conversation_id)
        conversation["status"] = "closed"
        self._save(conversation)
        return {
            "conversation_id": conversation_id,
            "status": "closed",
        }
