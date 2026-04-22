#!/usr/bin/env python3
"""On-disk primitives for the DM broker.

    ~/.mcp-broker/
      inbox/<encoded-identity>.log     # newline-delimited display-format lines, per-identity
      outbox/<encoded-identity>.log    # same, but for messages this identity sent
      cursors/<encoded-identity>.cursor  # byte offset into inbox log for read-cursor
      identities.json                  # registry of known identities
"""

import json
from pathlib import Path


def encode_identity(identity: str) -> str:
    """Filesystem-safe form of an identity. Replaces `/` with `_`."""
    return identity.replace("/", "_")


class InboxLog:
    """Append-only log of messages delivered to an identity."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def path_for(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.log"

    def append(self, identity: str, line: str) -> None:
        """Append `line` (no trailing newline) to the identity's inbox. Adds newline."""
        path = self.path_for(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")

    def read_from(self, identity: str, offset: int) -> tuple[list[str], int]:
        """Return (complete lines after `offset`, new byte offset after the last complete line).

        A trailing partial line (no newline terminator) is NOT returned and does
        NOT advance the offset — it'll be picked up once the writer finishes the line.
        """
        path = self.path_for(identity)
        if not path.exists():
            return [], offset
        with path.open("rb") as f:
            f.seek(offset)
            data = f.read()
        if not data:
            return [], offset
        last_nl = data.rfind(b"\n")
        if last_nl < 0:
            return [], offset
        complete = data[: last_nl + 1]
        lines = complete.decode().splitlines()
        return lines, offset + len(complete)


class OutboxLog:
    """Append-only log of messages sent by an identity."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def path_for(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.log"

    def append(self, identity: str, line: str) -> None:
        path = self.path_for(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")

    def read_all(self, identity: str) -> list[str]:
        path = self.path_for(identity)
        if not path.exists():
            return []
        return path.read_text().splitlines()


class CursorStore:
    """Per-identity byte offset into the inbox log."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def _path(self, identity: str) -> Path:
        return self.base_dir / f"{encode_identity(identity)}.cursor"

    def get(self, identity: str) -> int:
        path = self._path(identity)
        if not path.exists():
            return 0
        try:
            return int(path.read_text().strip())
        except ValueError:
            return 0

    def set(self, identity: str, offset: int) -> None:
        path = self._path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".cursor.tmp")
        tmp.write_text(str(offset))
        tmp.replace(path)


class IdentityRegistry:
    """Durable record of which identities have connected. Case-insensitive lookup."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._entries = json.loads(self.path.read_text())

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._entries, indent=2, sort_keys=True))
        tmp.replace(self.path)

    def _key(self, identity: str) -> str:
        return identity.lower()

    def touch(self, identity: str, now: str, wrote: bool) -> None:
        """Record a connection event. `wrote=True` also updates lastWriteAt."""
        key = self._key(identity)
        entry = self._entries.get(key, {})
        if "firstSeenAt" not in entry:
            entry["firstSeenAt"] = now
            entry["canonical"] = identity
        entry["lastSeenAt"] = now
        if wrote:
            entry["lastWriteAt"] = now
        self._entries[key] = entry
        self._save()

    def get(self, identity: str) -> dict | None:
        return self._entries.get(self._key(identity))

    def all(self) -> list[str]:
        return [e.get("canonical", k) for k, e in self._entries.items()]
