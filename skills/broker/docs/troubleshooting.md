# Broker Troubleshooting & Anti-patterns

Most scripting attempts on top of the broker reinvent things the CLI already does. If you're about to write a loop, a parser, or a dedup file, read this first.

## "I'm writing a `while true; broker read; sleep N` loop"

```bash
# DO NOT DO THIS
while true; do
  broker read
  sleep 10
done
```

**Why it's wrong.** The broker pushes new messages in real time over the Unix socket. Polling adds up to N seconds of latency per round trip, churns the cursor file, and burns tokens on the same header every iteration.

**Do this instead.**
```bash
broker follow --idle-timeout 120
```
Blocks, drains the backlog via the cursor, streams pushes as they arrive, exits on idle.

## "I ran `broker read` then `broker follow` and saw nothing"

`broker read` advances your cursor past the backlog. When you then call `broker follow`, there's nothing left to drain, so it waits silently for the next new message.

**Do this instead.** Skip the `read`. `broker follow` already drains unread backlog before it starts streaming — that's what it's for.

## "I'm parsing broker output with jq or python"

```bash
# DO NOT DO THIS
broker history | python3 -c 'import sys; [print(...) for line in sys.stdin]'
```

**Why it's wrong.** The line format `<ISO8601> [<sender> → you, other] <content>` IS the agent-facing format. You're the consumer. Reformatting it through another program wastes tokens and adds a failure mode.

**Do this instead.** Read the lines directly. If you want a filter, use `--from` / `--since` / `--sent` on `broker history`.

## "`reply-all` on a broadcast errors"

Broadcasts are fan-outs with no stable recipient set — by the time you'd "reply-all", the membership has already drifted (new identities register, some leave). So the broker refuses.

**Do this instead.** DM the broadcaster directly:
```bash
broker send --to <broadcaster-identity> "your reply"
```
If you want the thread to include others, list them explicitly with `--to a,b,c` and then use `reply-all --to-message` on that DM.

## "Reserved-identity error on connect"

The server refuses to bind `orchestrator`, `human`, or `BROADCAST` without a matching token file. `BROADCAST` is never claimable; the other two require `~/.mcp-broker/tokens/<identity>.token` to exist (any non-empty content). See `setup.md` for the token-file mechanism.

Most agents should use their cwd-derived identity anyway — reserved identities are for humans and orchestration processes.

## "Identity mismatch / I'm getting the wrong inbox"

Your cwd-derived identity and the `--identity` you're passing don't agree.

**Fix.** Run `broker whoami` in the exact cwd your agent is using. If it prints something you didn't expect, check:
- Nearest `package.json` `name` field (rule 1).
- `git remote get-url origin` (rule 2).
- Whether you're in a nested workspace where the nearest `package.json` isn't the one you think it is.

If you pass `--identity` explicitly, the broker trusts it — it does not reconcile against `whoami`. That's the lever for deliberately impersonating a different inbox (e.g. a human CLI sending as themselves from a repo workspace).

## "Deprecation warnings on create/join/leave"

Expected. The room-based commands (`create`, `join`, `leave`, `close`, `list`, `members`) still work for backward compatibility but print a warning to stderr. Replace them with DM commands when convenient:

- `create` + `send` → `broker send --to <recipients>`
- `join` → no-op; inboxes are per-identity, no joining required.
- `list` / `members` → `broker history` (+ `--from`, `--since`) to see who has been in your inbox.

## Troubleshooting real errors

### "Cannot connect to broker at /…/broker.sock. Is the broker server running?"

The server isn't running. Start it:

```bash
broker server
```

### `broker follow` exited with code 1 and "socket closed unexpectedly"

The server stopped or crashed mid-stream. On restart, your inbox log and cursor persist — call `broker follow` again to pick up where you left off.
