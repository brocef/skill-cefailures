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
