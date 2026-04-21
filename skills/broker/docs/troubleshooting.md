# Broker Troubleshooting & Anti-patterns

If you're about to write a bash loop or a python script to interact with the broker, read this first. Most attempts at scripting on top of the broker reinvent things the broker already does.

## Anti-pattern: `while true; broker read; sleep N` polling loop

```bash
# DO NOT DO THIS
while true; do
  result=$(broker read --identity me --socket /tmp/b.sock CID 2>/dev/null || echo '{"messages":[]}')
  echo "$result" | python3 -c "
import sys, json
for m in json.load(sys.stdin).get('messages', []):
  print(f\"[{m['sender']}] {m['content']}\", flush=True)
"
  sleep 10
done
```

**Why it's wrong:**
- The broker server already pushes new messages in real time over the Unix socket. Polling adds up to 10 seconds of latency per round-trip.
- The broker server already dedups by per-identity cursor; you do not need to track seen messages yourself.
- JSON parsing wastes tokens: you're already going to read the lines as your agent context.

**Do this instead:**
```bash
broker follow CID --identity me
```
Blocks, drains backlog, streams pushes, exits on idle or close.

## Anti-pattern: `/tmp/<cid>_seen.txt` dedup file

```bash
# DO NOT DO THIS
seen=/tmp/broker_${CID}_seen.txt
touch "$seen"
# ... parse output, append message ids to $seen, skip if seen, etc.
```

**Why it's wrong:**
- The broker server tracks a per-identity read cursor in the persisted conversation JSON. Each call to `broker read` (or the initial drain in `broker follow`) returns `messages[cursor:]` and advances the cursor. You never see the same message twice for the same identity.

**Do this instead:** trust the server. Stop maintaining a seen-file.

## Anti-pattern: `broker read | python -c '…'` JSON surgery

**Why it's wrong:** you're an LLM. Reading `[alice] hi` costs fewer tokens than reading the equivalent JSON. Feeding JSON through python just to reformat it is wasted computation that also wastes your context window.

**Do this instead:**
```bash
broker read CID --identity me --format compact
```
or use `broker follow`, which defaults to compact.

## Anti-pattern: `2>/dev/null || echo '{"messages":[]}'` error swallowing

**Why it's wrong:** the broker CLI exits non-zero only on real errors (server not running, conversation not found). Swallowing those hides genuine failures — your loop will silently not-receive messages while you think everything is fine.

**Do this instead:** let the CLI fail loudly. In a foreground script, non-zero exits are visible. In `broker follow`, socket drops produce a clear stderr error.

## Anti-pattern: Joining every room to see what's happening

**Why it's wrong:** the whole point of side conversations (see `patterns.md`) is that unrelated agents do not consume context on discussions that aren't for them. Joining a room costs you context on every message in that room.

**Do this instead:** stay in the main room. Read side rooms only when invited. Use `broker list` to see open rooms without joining.

## Troubleshooting real errors

### "Cannot connect to broker at /…/broker.sock. Is the broker server running?"

The server at `~/.mcp-broker/broker.sock` is not running. Ask the user to start it:

```bash
broker server --identity user
```

### `broker follow` exited with code 1 and "socket closed unexpectedly"

The server was stopped or crashed while you were following. The user can restart with `broker server`. On restart, the conversation persists — call `broker follow` again and you'll pick up where you left off via the cursor.

### `broker send` says "conversation is closed"

Someone called `broker close` on the conversation. It's read-only now. If you need to continue the discussion, create a new conversation.
