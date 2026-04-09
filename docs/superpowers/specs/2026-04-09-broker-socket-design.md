# MCP Broker Socket Architecture — Design Spec

Replace the file-based polling architecture with a Unix domain socket for real-time message routing. The socket server also serves as the human REPL interface. Disk persistence is retained for crash recovery and reconnection catch-up.

## Architecture

```
┌──────────────┐         ┌──────────────────────────────┐
│  Claude A    │◄─stdio─►│  mcp_broker.py               │
│  (agent_a)   │         │  (MCP server, socket client)  │◄──┐
└──────────────┘         └──────────────────────────────┘   │
                                                             │
┌──────────────┐         ┌──────────────────────────────┐   │  Unix
│  Claude B    │◄─stdio─►│  mcp_broker.py               │◄──┤  domain
│  (agent_b)   │         │  (MCP server, socket client)  │   │  socket
└──────────────┘         └──────────────────────────────┘   │
                                                             │
                         ┌──────────────────────────────┐   │
                         │  broker_cli.py --server       │◄──┘
                         │  (socket server + REPL)       │
                         │  persists to disk             │
                         └──────────────────────────────┘
                           │
                           ▼
                         ~/.mcp-broker/broker.sock
                         ~/.mcp-broker/conversations/*.json
```

- `broker_cli.py --server` is the hub — socket server, message router, disk persistence, and human REPL
- Each `mcp_broker.py` instance connects to the socket as a client
- Messages route in real-time through the socket; disk is for persistence/recovery
- The REPL shows incoming messages automatically (real-time for humans)
- MCP agents poll `read_new_messages` but it returns from an in-memory buffer (no file I/O)
- `broker_cli.py` without `--server` runs in client mode, connecting to the existing socket

## Socket Protocol (line-delimited JSON)

Each message is a JSON object followed by `\n`, sent over the Unix domain socket at `~/.mcp-broker/broker.sock`.

### Client-to-server messages

```json
{"type": "connect", "identity": "agent_a"}
{"type": "create_conversation", "topic": "...", "content": "optional seed"}
{"type": "join_conversation", "conversation_id": "abc123"}
{"type": "send_message", "conversation_id": "abc123", "content": "..."}
{"type": "read_new_messages", "conversation_id": "abc123"}
{"type": "list_conversations", "status": "open"}
{"type": "close_conversation", "conversation_id": "abc123"}
```

### Server-to-client messages

```json
{"type": "response", "request_type": "create_conversation", "data": {...}}
{"type": "response", "request_type": "list_conversations", "data": {...}}
{"type": "message", "conversation_id": "abc123", "message": {"id": "...", "sender": "agent_b", "content": "...", "timestamp": "..."}}
{"type": "system", "conversation_id": "abc123", "event": "join", "identity": "agent_a"}
{"type": "system", "conversation_id": "abc123", "event": "leave", "identity": "agent_a"}
```

### Protocol behavior

- `connect` is the first message a client sends — registers its identity with the server
- `message` is pushed in real-time to all connected members of the conversation (except the sender)
- `system` events (join/leave) are broadcast to all members of the conversation
- `response` is the synchronous reply to a client request

## Conversation Membership

Connecting to the socket registers your identity but does not join any conversation. Membership is per-conversation and explicit:

- `create_conversation` auto-joins the creator
- `send_message` auto-joins the sender
- `join_conversation` explicitly joins
- `close_conversation` removes membership (conversation becomes read-only)
- `read_new_messages` does not join — a client can read without becoming a member (no system message, no real-time routing)
- Disconnect broadcasts `leave` to every conversation the client was a member of

The server tracks `members: dict[conversation_id, set[identity]]`. Messages are routed only to connected members of the target conversation.

## Server (`broker_cli.py --server`)

Starts with `python scripts/broker_cli.py --server`. Combines three roles:

### Socket server
- Listens on Unix domain socket at `~/.mcp-broker/broker.sock`
- Accepts client connections, tracks connected identities and conversation membership
- Routes messages only to members of the target conversation
- Broadcasts system join/leave events per-conversation
- On client disconnect, broadcasts leave events to all conversations the client was in

### Persistence
- All conversations are persisted to disk in the existing JSON format (`~/.mcp-broker/conversations/*.json`)
- On startup, loads existing conversations from disk into memory
- System messages are stored in the messages array with `"sender": "system"`

### REPL
- The server's own identity (default `"user"`, configurable via `--identity`)
- In conversation mode, incoming messages print automatically — no need to type `read`
- Lobby commands unchanged: `list`, `create`, `join`, `exit`

### Client mode (no `--server`)

`broker_cli.py` without `--server` connects to the existing socket as a client. Same REPL interface, but relies on a running server. This lets a user participate from a separate terminal.

## MCP Broker Changes (`mcp_broker.py`)

Shifts from direct file I/O to socket client:

- On startup, connects to `~/.mcp-broker/broker.sock` and sends `connect` with its identity
- Maintains an in-memory buffer of conversations and messages received from the socket
- Tool calls (`create_conversation`, `send_message`, etc.) send a request over the socket and wait for a `response`
- Incoming `message` events update the in-memory buffer asynchronously
- `read_new_messages` returns from the buffer instantly
- If the socket is unavailable, falls back to direct file I/O via the existing `ConversationStore` (backwards compatible)

## System Messages

Stored in the conversation's messages array:

```json
{"id": "msg-...", "sender": "system", "content": "agent_a joined", "timestamp": "..."}
```

- Generated on join (explicit or auto-join via create/send) and leave (disconnect or close)
- Broadcast to all members of the conversation
- Included in `read_new_messages` responses
- Counted in `message_count` in `list_conversations`

## Files

| File | Changes |
|------|---------|
| `scripts/broker_cli.py` | Add `--server` mode with socket server + REPL. Without `--server`, connect as socket client. |
| `scripts/mcp_broker.py` | Add socket client alongside existing `ConversationStore`. Socket is primary, file I/O is fallback. |
| `tests/test_broker_server.py` | New — socket server routing, membership, persistence, system messages |
| `tests/test_mcp_broker.py` | Add socket client tests, keep existing tests for file I/O fallback |
| `tests/test_broker_cli.py` | Update for server/client modes |

## Dependencies

- `asyncio` (stdlib) for socket server and async I/O
- No new external dependencies

## Not in scope

- MCP resource subscriptions for proactive agent notifications (tracked in TODO.md)
- Authentication or encryption (local-only, trust is ambient)
- Multi-machine support (Unix domain socket is local)
