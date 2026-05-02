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

**Do this instead.** Enter Broker Mode:
```
/broker-mode
```
The slash command runs the canonical recv/process/reply loop for you. `broker recv` is the underlying primitive — it blocks, drains the backlog via the cursor, and returns the next batch.

## "I ran `broker read` then `broker recv` and saw nothing"

`broker read` advances your cursor past the backlog. When you then call `broker recv`, there's nothing left to drain, so it waits silently for the next new message.

**Do this instead.** Skip the `read`. `broker recv` already drains unread backlog before it waits for new arrivals — that's what it's for.

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

## "Identity mismatch / I'm getting the wrong inbox"

Your cwd-derived identity and the `--identity` you're passing don't agree.

**Fix.** Run `broker whoami` in the exact cwd your agent is using. If it prints something you didn't expect, check:
- Nearest `package.json` `name` field (rule 1).
- `git remote get-url origin` (rule 2).
- Whether you're in a nested workspace where the nearest `package.json` isn't the one you think it is.

If you pass `--identity` explicitly, the broker trusts it — it does not reconcile against `whoami`. That's the lever for deliberately impersonating a different inbox (e.g. a human CLI sending as themselves from a repo workspace).

## "`broker recv` exited with 'identity X already has an active follower'"

Two `broker recv` processes resolved to the same identity (most often: two
terminals in the same workspace, since identity is derived from cwd). Only one
follower is allowed per identity at a time. The `follower` wording in the
server-side error string reflects the unchanged internal protocol mode; the
user-facing primitive is `broker recv`.

**Fix.** Stop one of them, or pin a different identity for one workspace via
`broker init --identity <other-name>`.

## Troubleshooting real errors

### "Cannot connect to broker at /…/broker.sock. Is the broker server running?"

The server isn't running. Start it:

```bash
broker server
```

### `broker recv` exited with code 1 and "socket closed unexpectedly"

The server stopped or crashed mid-stream. With the socketed presence model, this is now the
expected exit path: when the broker server goes away, every active `broker recv`
exits non-zero so the agent learns that presence has dropped.

On restart, your inbox log and cursor persist — call `broker recv` again to
pick up where you left off. Any DMs sent while the server was down were rejected
at the sender (the sender will have seen the same Cannot-connect error), so
nothing is silently lost.

**Broker Mode does not retry on connection failure.** If the server is restarting when `broker recv` is called, `recv` exits non-zero, the agent reports the failure, and the loop ends. The user re-invokes `/broker-mode` once `broker server` is back. This is a deliberate trade — explicit failure beats hidden retries that could mask real outages.
