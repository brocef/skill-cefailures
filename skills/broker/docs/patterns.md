# Broker Usage Patterns

Canonical ways to use the broker in a multi-agent Claude Code setup.

## Pattern: Wait for a reply

When you've sent a message and expect the other agent to respond, use `broker follow` in the foreground. It blocks until replies arrive, then returns.

```bash
broker send --identity server ROOM "Pushed v1.2.3, please bump the dep"
broker follow ROOM --identity server --idle-timeout 120
```

`broker follow` will:
1. Drain any backlog you haven't read yet.
2. Print each incoming message as `[sender] content`.
3. Return when the conversation goes quiet for `--idle-timeout` seconds.

Adjust `--idle-timeout` to match how long you're willing to wait before giving up. For short questions, 60s is reasonable. For long-running work (e.g. "publish a package"), use 600s or disable with `--idle-timeout 0`.

To wait for exactly one reply and exit:

```bash
broker follow ROOM --identity server --count 1
```

## Pattern: Side conversation (DM-style) between two agents

When two agents need to discuss something in depth that other agents should not have to read (e.g. API change requests, debugging sessions), fork a dedicated conversation.

Naming convention: `{a}-{b}-{topic}-{YYYYMMDD-HHMMSS}`. Example:

```bash
# server agent creates a focused conversation with core
broker create --identity server "server-core-change-request-20260421-1530" \
  --content "We need to change the validate() signature. Joining…"
# ^ returns a conversation_id; share it with core
broker send --identity server MAIN_ROOM \
  "QUESTION: @core let's continue in server-core-change-request-20260421-1530 (ID: <cid>)"
```

Lifecycle:
- Create the side room; seed with the topic.
- Invite the other agent via a message in the main room (or let them join by ID).
- Work the discussion to a conclusion.
- Post the outcome back to the main room as a `DECISION:` or `READY:` signal.
- `broker close` the side room when done — it stays on disk for audit but drops out of `broker list`.

Other agents should **not join** side rooms unless explicitly invited — the naming convention makes the ownership obvious.

## Pattern: Short signals in the main room

Use short, structured signals in the top-level coordination room (one per repo or per initiative). Examples:

```
[server] READY: v1.2.3 published
[core] BLOCKED: server TypeError on validate()
[server] QUESTION: @core should validate() take a schema or a raw object?
[server] DECISION: side conv → validate(schema) wins
```

See `signals.md` for the full vocabulary.

## Pattern: Stream messages while working (rare)

If you're doing other work but still want to react to messages as they arrive, run `broker follow` in the background via the Monitor tool. Each printed line becomes a Monitor notification you can respond to on your next turn.

```bash
broker follow ROOM --identity server --idle-timeout 0 --timeout 1800
# ^ run under Monitor; idle disabled so the stream doesn't exit while you work
```

Use sparingly: every incoming line consumes agent context. Prefer foreground `broker follow` when you're explicitly waiting.

## Anti-patterns

See `troubleshooting.md`. If you're about to write a bash loop, read that doc first.
