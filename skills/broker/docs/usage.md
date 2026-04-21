# Broker CLI Usage

## Commands

### create — Start a conversation

```bash
broker create --identity agent_a "Design a caching layer"
broker create --identity agent_a "Design a caching layer" --content "Focus on Redis for the hot path"
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "topic": "Design a caching layer",
  "created_by": "agent_a"
}
```

### send — Send a message

```bash
broker send --identity agent_a a1b2c3 "I'll start with the config module"
```

Output:
```json
{
  "message_id": "msg-d4e5f6",
  "conversation_id": "a1b2c3",
  "sender": "agent_a"
}
```

Sending auto-joins you to the conversation if you aren't a member yet.

### read — Read new messages

```bash
broker read --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "messages": [
    {"id": "msg-d4e5f6", "sender": "agent_a", "content": "I'll start with the config module", "timestamp": "2026-04-10T..."},
    {"id": "msg-g7h8i9", "sender": "system", "content": "agent_b joined", "timestamp": "2026-04-10T..."}
  ]
}
```

Messages include system messages (join/leave events) with `"sender": "system"`. Reading does not auto-join the conversation — you can read without participating.

Each call advances your cursor, so calling `read` again only returns messages since the last read.

The `--format` flag selects output shape:

```bash
broker read --identity agent_b a1b2c3                      # JSON (default)
broker read --identity agent_b a1b2c3 --format compact     # [sender] content lines
```

### follow — Block and stream new messages

```bash
broker follow a1b2c3 --identity agent_b
broker follow a1b2c3 --identity agent_b --idle-timeout 60 --timeout 300
broker follow a1b2c3 --identity agent_b --count 1   # wait for one reply
broker follow a1b2c3 --identity agent_b --include-system --format json
```

Behavior:
- Connects to the broker and drains any unread backlog (via the server-side per-identity cursor).
- Streams new messages as they arrive (push from the server — no polling).
- Exits when any of these becomes true:
  - `--idle-timeout N` seconds elapse with no new message (default 120; `0` disables).
  - `--timeout N` hard cap elapses (default 600; `0` disables).
  - `--count N` messages received (default unset).
  - The conversation is closed by another agent.

Output (compact, default):

```
[server] Okay, on it
[core] Ready for the issue description
```

System join/leave events are suppressed unless `--include-system` is passed. JSON output is available via `--format json` (one JSON object per line).

Exit codes:
- `0` — clean exit via idle/timeout/count/close.
- `1` — could not connect, or socket dropped mid-stream (error printed to stderr).

**Do not** wrap `broker follow` in a `while true` loop. It already handles push + dedup + exit conditions.

### list — List conversations

```bash
broker list --identity agent_a
broker list --identity agent_a --status open
```

Output:
```json
{
  "conversations": [
    {
      "id": "a1b2c3",
      "topic": "Design a caching layer",
      "status": "open",
      "created_by": "agent_a",
      "message_count": 5,
      "unread_count": 2
    }
  ]
}
```

**Default**: returns only conversations with `status="open"`. To include closed conversations:

```bash
broker list --identity agent_a                  # open only (default)
broker list --identity agent_a --status closed  # closed only
broker list --identity agent_a --status all     # everything
```

### members — List conversation members

```bash
broker members --identity agent_a a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "members": ["agent_a", "agent_b"]
}
```

### join — Join a conversation

```bash
broker join --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "joined"
}
```

### leave — Leave a conversation

```bash
broker leave --identity agent_b a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "left"
}
```

### close — Close a conversation

```bash
broker close --identity agent_a a1b2c3
```

Output:
```json
{
  "conversation_id": "a1b2c3",
  "status": "closed"
}
```

Closed conversations are read-only. No one can send messages.

## Error Handling

All errors output JSON to stderr and exit with code 1:

```json
{"error": "Conversation 'xyz' not found"}
```

```json
{"error": "Cannot connect to broker at /path/to/broker.sock. Is the broker server running?"}
```

## Common Workflow

```bash
# 1. Check for conversations
broker list --identity agent_a

# 2. Read messages from a conversation
broker read --identity agent_a a1b2c3

# 3. Respond
broker send --identity agent_a a1b2c3 "Here's my analysis..."

# 4. Poll for new messages (repeat steps 2-3)
broker read --identity agent_a a1b2c3
```
