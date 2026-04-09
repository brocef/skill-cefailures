# MCP Message Broker Spec

A lightweight MCP server that enables two Claude Code instances to hold structured conversations. Each instance connects to the same server and is assigned an identity. Messages are persisted to disk so conversations survive server restarts.

## Architecture

```
┌──────────────┐         ┌─────────────┐         ┌──────────────────┐
│ agent-a│◄───MCP──►│ mcp-broker  │◄───MCP──►│ agent-b  │
│  (identity:  │         │ (file-backed│         │  (identity:      │
│  "agent_a")     │         │  storage)   │         │  "agent_b")       │
└──────────────┘         └─────────────┘         └──────────────────┘
```

Both instances declare the same MCP server in their `.claude/settings.json`. The broker distinguishes them by identity, passed as a CLI argument.

## Configuration

Each project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "broker": {
      "command": "node",
      "args": ["/path/to/mcp-broker/index.js", "--identity", "agent_a"],
      "type": "stdio"
    }
  }
}
```

The `--identity` argument is a short string (e.g., `"agent_a"`, `"agent_b"`) that tags outgoing messages with a sender.

## Storage

Conversations are stored as JSON files in a configurable directory (default: `~/.mcp-broker/conversations/`). Each conversation is a single file named `{conversation_id}.json`.

```
~/.mcp-broker/
  conversations/
    a1b2c3.json
    d4e5f6.json
```

### Conversation file format

```json
{
  "id": "a1b2c3",
  "topic": "Add claimId validation to core",
  "status": "open",
  "createdBy": "agent_b",
  "createdAt": "2026-04-09T14:30:00Z",
  "messages": [
    {
      "id": "msg-001",
      "sender": "agent_b",
      "content": "I need core to expose a validateClaimId function...",
      "timestamp": "2026-04-09T14:30:05Z"
    },
    {
      "id": "msg-002",
      "sender": "agent_a",
      "content": "ClaimLibrary already has a has() method...",
      "timestamp": "2026-04-09T14:31:12Z"
    }
  ],
  "cursors": {
    "agent_a": 1,
    "agent_b": 2
  }
}
```

The `cursors` object tracks the last message index each identity has read. `read_new_messages` returns messages after the caller's cursor and advances it.

## Tools

### `create_conversation`

Start a new dialogue.

| Parameter | Type   | Required | Description                        |
|-----------|--------|----------|------------------------------------|
| `topic`   | string | yes      | Short description of the dialogue  |

**Returns:**

```json
{
  "conversation_id": "a1b2c3",
  "topic": "Add claimId validation to core",
  "created_by": "agent_b"
}
```

### `send_message`

Append a message to an existing conversation.

| Parameter         | Type   | Required | Description              |
|-------------------|--------|----------|--------------------------|
| `conversation_id` | string | yes      | Target conversation      |
| `content`         | string | yes      | Message body (markdown)  |

**Returns:**

```json
{
  "message_id": "msg-003",
  "conversation_id": "a1b2c3",
  "sender": "agent_a"
}
```

**Errors:** Conversation not found. Conversation closed.

### `read_new_messages`

Read messages not yet seen by the calling identity.

| Parameter         | Type   | Required | Description         |
|-------------------|--------|----------|---------------------|
| `conversation_id` | string | yes      | Target conversation |

**Returns:**

```json
{
  "conversation_id": "a1b2c3",
  "messages": [
    {
      "id": "msg-002",
      "sender": "agent_b",
      "content": "Can you also check if...",
      "timestamp": "2026-04-09T14:35:00Z"
    }
  ],
  "remaining_unread": 0
}
```

Returns an empty `messages` array if there is nothing new. The cursor advances automatically.

### `list_conversations`

List all conversations, optionally filtered by status.

| Parameter | Type   | Required | Description                            |
|-----------|--------|----------|----------------------------------------|
| `status`  | string | no       | Filter: `"open"`, `"closed"`, or omit for all |

**Returns:**

```json
{
  "conversations": [
    {
      "id": "a1b2c3",
      "topic": "Add claimId validation to core",
      "status": "open",
      "created_by": "agent_b",
      "message_count": 4,
      "unread_count": 1
    }
  ]
}
```

`unread_count` is relative to the calling identity's cursor.

### `close_conversation`

Mark a conversation as closed. Closed conversations are read-only.

| Parameter         | Type   | Required | Description         |
|-------------------|--------|----------|---------------------|
| `conversation_id` | string | yes      | Target conversation |

**Returns:**

```json
{
  "conversation_id": "a1b2c3",
  "status": "closed"
}
```

## Behavior notes

- **Identity is per-connection.** Two connections with the same identity are treated as the same participant (shared cursor). This means if you restart Claude Code, it picks up where it left off.
- **No authentication.** This is a local-only tool. Trust is ambient.
- **Conversation IDs** are short random strings (nanoid or similar). Not UUIDs — they'll appear in tool calls frequently so brevity helps.
- **File locking** is not required for the expected use case (two instances, low write frequency). If writes ever collide, last-write-wins is acceptable.
- **No TTL or cleanup.** Conversations accumulate until manually deleted. A future `purge_closed` tool could handle this if needed.
- **Content format.** Message content is freeform markdown. No schema enforcement — agents decide what to send.
