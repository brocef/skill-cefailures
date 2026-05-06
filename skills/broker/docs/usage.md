# Broker CLI Usage

Full reference for the DM/inbox CLI. For how to wire these together, see `patterns.md`.

## Quick reference

| Command | Description |
|---------|-------------|
| `broker whoami` | Print the identity the CLI will use from this cwd |
| `broker send --to a,b CONTENT` | DM one or more recipients |
| `broker broadcast CONTENT` | Fan out to every registered identity |
| `broker reply-all --to-message MID CONTENT` | Reply to all recipients of a prior DM, excluding self |
| `broker recv [--timeout N] [--burst-window M]` | Receive the next batch: wait for first arrival, drain follow-ups for `M` seconds (default 5), exit. Used inside Broker Mode. |
| `broker history [--from X] [--since ISO] [--sent]` | Read inbox (or outbox) without advancing the cursor |
| `broker read` | Advance cursor; print only new inbox lines since last read |
| `broker clients` | List known identities and their presence status |
| `broker server` | Start the broker server with an interactive REPL |

## Storage layout

Everything lives under `~/.mcp-broker/`:

- `inbox/<encoded-identity>.log` — newline-delimited display-format lines for messages you received.
- `outbox/<encoded-identity>.log` — same shape, for messages you sent.
- `cursors/<encoded-identity>.cursor` — byte offset into the inbox log; advanced by `broker read`.
- `identities.json` — registry of known identities (`firstSeenAt`, `lastSeenAt`, `lastWriteAt`, `canonical`).
- `messages/<message-id>.json` — raw records used by `reply-all` to look up recipient sets.
- `broker.sock` — Unix socket the CLI talks to.

**Identity encoding:** `/` becomes `_` in filenames. So `@myorg/projectA` → `inbox/@myorg_projectA.log`.

## Message display format

Each inbox/outbox line has the form `<ISO8601> [<header>] <content>`, with three header shapes:

```
2026-04-22T10:15:03Z [projectA-server] READY: shared v1.2.3 published
2026-04-22T10:15:47Z [projectA-server → you, @myorg_projectB] QUESTION: who owns the migration?
2026-04-22T10:16:02Z [@orchestrator/myorg → BROADCAST] npm registry is down
```

- **Single recipient:** just `[<sender>]` — the viewer is the sole recipient, inferred from context.
- **Multi-recipient:** `[<sender> → you, other1, other2]` — the viewer appears as `you`, other recipients listed as their identities.
- **Broadcast:** `[<sender> → BROADCAST]`.

Content newlines are escaped as `\n`; backslashes as `\\`. That's it — there is no JSON to parse.

## CLI reference

### whoami

```
broker whoami
```

Print the identity that the CLI will use from the current cwd. Resolution order: `BROKER_IDENTITY` env var (validated for `@orchestrator/...` shape), then a walk up looking for `.broker/config.json` (within `$HOME`) or `package.json` — whichever is closest to cwd wins (same-dir tie goes to `.broker/config.json`), then `git remote origin`. Useful to confirm which inbox you'll write to before sending.

Example:
```bash
$ broker whoami
@myorg/projectA
```

### send — DM one or more recipients

```
broker send --to <csv-of-identities> [--identity <me>] <content>
```

Send a DM. `--identity` is auto-filled from cwd if omitted. `--to` takes a comma-separated list of identities. Returns the message ID on stdout.

- `--to a,b,c` — recipients (required).
- `--identity X` — override sender (defaults to `broker whoami`).
- Positional `CONTENT` — the message body. Use standard shell quoting.

Example:
```bash
$ broker send --to projectA-server "READY: shared v1.2.3 published"
msg-7f3a91
```

### broadcast — fan out to every registered identity

```
broker broadcast [--identity <me>] <content>
```

Delivers to every identity currently in `identities.json` except the sender. Recipients see `[<sender> → BROADCAST] <content>`.

Example:
```bash
$ broker broadcast "BLOCKED: npm registry is down, pausing publishes"
msg-b12c04
```

### reply-all — reply to all recipients of a prior DM

```
broker reply-all --to-message <MID> [--identity <me>] <content>
```

Looks up the recipient set of message `<MID>` in `messages/<MID>.json`, then sends a new DM to `(sender ∪ recipients) − self`. Errors if the target message is a broadcast (no stable recipient set).

- `--to-message MID` — the message to reply to (required).
- Positional `CONTENT` — the reply body.

Example:
```bash
$ broker reply-all --to-message msg-7f3a91 "DECISION: schema wins"
msg-e9d201
```

### recv — receive the next batch

```
broker recv [--timeout N] [--burst-window M] [--identity <me>]
```

Block until a batch is available, then return it. Used by Broker Mode (see `patterns.md`).

- `--timeout N` — max seconds to wait for the first message. Default `0` (no upper bound). Only consulted when the inbox is empty at startup; backlog at startup short-circuits this entirely.
- `--burst-window M` — seconds to keep tailing for follow-ups after the first arrival. Default `5`. Hard cap; does not extend on each new arrival. Setting `0` exits as soon as the first arrival has been delivered.
- `--identity X` — override the cwd-derived identity.
- `--show-ids` — prefix each emitted line with the message ID (useful for `reply-all`).

Exits cleanly (code 0) on timeout-with-no-traffic or burst-window completion. Non-zero on socket error or server-disconnect.

`broker recv` opens a presence socket for its full duration. While it is running, your identity is shown as "live" by `broker clients`; while you are processing the batch (between `recv` calls), you appear "offline." This is intended: presence reflects readiness to receive.

Example:
```bash
$ broker recv --burst-window 5
2026-04-22T10:15:03Z [projectA-server] READY: shared v1.2.3 published
2026-04-22T10:15:47Z [projectA-server → you, @myorg_projectB] QUESTION: who owns the migration?
```

### history — read without advancing the cursor

```
broker history [--from <identity>] [--since <ISO8601>] [--sent] [--identity <me>]
```

Dump inbox (or outbox with `--sent`) as display lines. Does not touch the read cursor — safe to call repeatedly.

- `--from X` — only messages from identity X.
- `--since ISO` — only messages at or after this timestamp.
- `--sent` — read from outbox instead of inbox.
- `--identity X` — override cwd-derived identity.

Example:
```bash
$ broker history --from @orchestrator/myorg --since 2026-04-22T09:00:00Z
2026-04-22T09:45:10Z [@orchestrator/myorg → you] catch up on #1234 when you're free
```

### read — drain new lines, advance cursor

```
broker read [--identity <me>]
```

Print only inbox lines newer than the stored cursor, then advance the cursor to the end. Useful in scripted one-shots where you explicitly want to consume-and-mark.

Example:
```bash
$ broker read
2026-04-22T10:15:47Z [projectA-server → you, @myorg_projectB] QUESTION: who owns the migration?
```

**Do not chain `read` → `recv`.** Read advances the cursor, so `recv` will see nothing until the next new message. Use `recv` alone; it handles drain + wait.

### clients — list connected identities

```
broker clients [--identity <me>]
```

Print every known identity with their presence status. Live identities hold an active socket connection; offline identities are registered but not currently connected. With Broker Mode, "live" means the agent is currently waiting in `broker recv`. Between iterations of the loop (while the agent is processing or replying), it is shown as "offline" — that is the expected behavior, not a failure. Useful for confirming who is reachable before sending a DM.

Example:
```bash
$ broker clients
  alpha       live, since 2026-05-01T15:30:12Z
  user        live, since 2026-05-01T15:29:00Z (you)
  zeta        offline, last seen 2026-04-29T10:00:00Z
```

### server — start the broker with an interactive REPL

```
broker server [--identity <me>] [--root-dir <path>]
```

Boot the broker server and drop into an interactive REPL on stdin. The REPL identity defaults to `user`; pass `--identity @orchestrator/<scope>` to drive the broker as the workspace orchestrator. From the REPL:

```
broker> who
broker> send <identity[,identity]> <text>
broker> broadcast <text>
broker> read | history
broker> emit-messages on|off
broker> help | exit
```

The `who` command shows all known identities with their presence status:

```
broker> who
  alpha       live, since 2026-05-01T15:30:12Z
  user        live, since 2026-05-01T15:29:00Z (you)
  zeta        offline, last seen 2026-04-29T10:00:00Z
```

Live identities hold an active presence socket; offline identities are registered but not currently connected.

Toggling `emit-messages on` echoes a copy of every message the broker routes — handy when you want a live audit tail of what's flowing through.
