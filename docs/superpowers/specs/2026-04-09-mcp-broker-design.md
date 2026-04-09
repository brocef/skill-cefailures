# MCP Message Broker — Design Spec

A lightweight MCP server that enables two Claude Code instances on the same machine to hold structured conversations. Each instance connects to the same server (via stdio) and is assigned an identity. Messages are persisted to disk as JSON files so conversations survive restarts.

## Architecture

```
┌──────────────┐         ┌─────────────┐         ┌──────────────────┐
│  Instance A  │◄──MCP──►│ mcp-broker  │◄──MCP──►│   Instance B     │
│ (identity:   │  stdio  │ (file-backed│  stdio  │ (identity:       │
│  "core")     │         │  storage)   │         │  "server")       │
└──────────────┘         └─────────────┘         └──────────────────┘
```

Each Claude Code instance declares the broker as an MCP server in its project's `.claude/settings.json` with a distinct `--identity` argument. The broker distinguishes participants by identity. Two connections with the same identity share a cursor (so restarts pick up where they left off).

## Approach

**Approach B: ConversationStore class + FastMCP.** A `ConversationStore` class encapsulates all file I/O and conversation logic. MCP tool handlers are thin wrappers that delegate to the store. This cleanly separates concerns and makes the store independently testable.

## Files

| File | Purpose |
|------|---------|
| `scripts/mcp_broker.py` | MCP server — `ConversationStore` class + FastMCP thin layer |
| `scripts/install_broker.py` | Wires the broker into a project's `.claude/settings.json` |
| `tests/test_mcp_broker.py` | Tests `ConversationStore` in isolation |
| `tests/test_install_broker.py` | Tests install/remove/overwrite/error behavior |

## ConversationStore

```python
class ConversationStore:
    def __init__(self, identity: str, storage_dir: Path) -> None: ...

    # Public API — one method per MCP tool
    def create_conversation(self, topic: str) -> dict
    def send_message(self, conversation_id: str, content: str) -> dict
    def read_new_messages(self, conversation_id: str) -> dict
    def list_conversations(self, status: str | None = None) -> dict
    def close_conversation(self, conversation_id: str) -> dict

    # Private helpers
    def _load(self, conversation_id: str) -> dict
    def _save(self, conversation: dict) -> None
    def _generate_id(self) -> str      # secrets.token_hex(3) -> 6-char hex
    def _message_id(self) -> str        # "msg-" + _generate_id()
```

### Behavior

- Each public method returns a plain dict matching the spec's JSON response shapes.
- `_generate_id()` uses `secrets.token_hex(3)` for short 6-char hex IDs.
- Timestamps use `datetime.now(timezone.utc).isoformat()`.
- Storage dir is created on first write via `mkdir(parents=True, exist_ok=True)`.
- No file locking — last-write-wins per the spec.
- Errors (conversation not found, conversation closed) raise `ValueError` with a descriptive message. FastMCP converts unhandled exceptions into tool error responses.
- A missing cursor entry for an identity is treated as 0 (i.e., all messages are unread). Cursors are created lazily — `create_conversation` only initializes the creator's cursor.

### Conversation file format

Stored in `<storage_dir>/<conversation_id>.json`:

```json
{
  "id": "a1b2c3",
  "topic": "Add claimId validation to core",
  "status": "open",
  "createdBy": "server",
  "createdAt": "2026-04-09T14:30:00+00:00",
  "messages": [
    {
      "id": "msg-001",
      "sender": "server",
      "content": "I need core to expose a validateClaimId function...",
      "timestamp": "2026-04-09T14:30:05+00:00"
    }
  ],
  "cursors": {
    "core": 0,
    "server": 1
  }
}
```

The `cursors` object tracks the last message index each identity has read. `read_new_messages` returns messages after the caller's cursor and advances it.

### Tool return shapes

**create_conversation(topic)**
```json
{"conversation_id": "a1b2c3", "topic": "...", "created_by": "server"}
```

**send_message(conversation_id, content)**
```json
{"message_id": "msg-003", "conversation_id": "a1b2c3", "sender": "core"}
```
Errors: conversation not found, conversation closed.

**read_new_messages(conversation_id)**
```json
{
  "conversation_id": "a1b2c3",
  "messages": [{"id": "msg-002", "sender": "server", "content": "...", "timestamp": "..."}],
  "remaining_unread": 0
}
```
Returns empty `messages` array if nothing new. Cursor advances automatically.

**list_conversations(status=None)**
```json
{
  "conversations": [
    {"id": "a1b2c3", "topic": "...", "status": "open", "created_by": "server", "message_count": 4, "unread_count": 1}
  ]
}
```
`unread_count` is relative to the calling identity's cursor. Optional `status` filter: `"open"`, `"closed"`, or omit for all.

**close_conversation(conversation_id)**
```json
{"conversation_id": "a1b2c3", "status": "closed"}
```

## MCP Layer

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-broker")
store: ConversationStore  # initialized in main() after parsing CLI args

@mcp.tool()
def create_conversation(topic: str) -> dict:
    """Start a new conversation."""
    return store.create_conversation(topic)

# ... same thin-wrapper pattern for all 5 tools
```

- `argparse` handles `--identity` (required) and `--storage-dir` (optional, default `~/.mcp-broker/conversations`).
- The `store` is initialized in `main()` after arg parsing, assigned to module level.
- `mcp.run()` starts the stdio transport.
- Tool descriptions come from docstrings (FastMCP extracts them automatically).

### Configuration

Each project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "broker": {
      "command": "python",
      "args": ["/absolute/path/to/scripts/mcp_broker.py", "--identity", "core"],
      "type": "stdio"
    }
  }
}
```

## Install Script

`scripts/install_broker.py` wires the broker into a project's `.claude/settings.json`.

```
python scripts/install_broker.py --identity core
python scripts/install_broker.py --identity server --project-dir /path/to/other/project
python scripts/install_broker.py --identity core --storage-dir /custom/path
python scripts/install_broker.py --remove
```

### Behavior

- Reads (or creates) `<project-dir>/.claude/settings.json`.
- Adds/updates the `mcpServers.broker` entry with the absolute resolved path to `mcp_broker.py`, the given identity, and `"type": "stdio"`.
- `--project-dir` defaults to the current working directory.
- `--storage-dir` is an optional pass-through (included in broker args if provided).
- `--remove` removes the `broker` entry from `mcpServers`.
- If `.claude/` directory does not exist, prints an error to stderr and exits with code 1.
- Preserves all other keys in settings.json — only touches `mcpServers.broker`.
- If the broker entry already exists, overwrites it (e.g., to change identity).

## Testing

### test_mcp_broker.py

Tests `ConversationStore` directly using `tmp_path`:

- **create:** returns correct shape, file exists on disk
- **send_message:** appends message, correct sender from identity
- **send to closed:** raises `ValueError`
- **read_new_messages:** returns only unread messages, advances cursor, returns empty when caught up
- **cursor isolation:** two stores with different identities on the same storage dir have independent cursors
- **list_conversations:** returns all, filters by status, `unread_count` is identity-relative
- **close_conversation:** sets status to closed
- **not found:** raises `ValueError` for nonexistent conversation ID

### test_install_broker.py

Tests using `tmp_path`:

- **install:** writes correct entry to settings.json, preserves other keys
- **overwrite:** re-running with different identity updates the entry
- **remove:** `--remove` deletes the broker entry
- **no .claude dir:** exits with error

## Dependencies

Add `mcp>=1.0.0` to `requirements.txt` as a required dependency. Everything else is stdlib (`json`, `pathlib`, `secrets`, `argparse`, `datetime`).
