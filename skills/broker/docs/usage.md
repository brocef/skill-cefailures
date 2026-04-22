# Broker CLI Usage

Full reference for the DM/inbox CLI. For how to wire these together, see `patterns.md`.

## Storage layout

Everything lives under `~/.mcp-broker/`:

- `inbox/<encoded-identity>.log` — newline-delimited display-format lines for messages you received.
- `outbox/<encoded-identity>.log` — same shape, for messages you sent.
- `cursors/<encoded-identity>.cursor` — byte offset into the inbox log; advanced by `broker read`.
- `identities.json` — registry of known identities (`firstSeenAt`, `lastSeenAt`, `lastWriteAt`, `canonical`).
- `messages/<message-id>.json` — raw records used by `reply-all` to look up recipient sets.
- `tokens/<identity>.token` — per-host token files for reserved identities (`orchestrator`, `human`).
- `broker.sock` — Unix socket the CLI talks to.
- `conversations/` — legacy room state (deprecated, kept for old `create`/`join`/`leave`).

**Identity encoding:** `/` becomes `_` in filenames. So `@proposit/shared` → `inbox/@proposit_shared.log`.

## Message display format

Each inbox/outbox line has the form `<ISO8601> [<header>] <content>`, with three header shapes:

```
2026-04-22T10:15:03Z [proposit-server] READY: shared v1.2.3 published
2026-04-22T10:15:47Z [proposit-server → you, @proposit_core] QUESTION: who owns the migration?
2026-04-22T10:16:02Z [orchestrator → BROADCAST] npm registry is down
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

Print the identity derived from the current cwd using the 2-rule algorithm (package.json `name`, then `git remote origin`). Useful to confirm which inbox you'll write to before sending.

Example:
```bash
$ broker whoami
@proposit/shared
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
$ broker send --to proposit-server "READY: shared v1.2.3 published"
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

### follow — block, drain, stream

```
broker follow [--idle-timeout N] [--identity <me>]
```

Tail the per-identity inbox log. Drains unread backlog first (advancing the cursor as it goes), then streams new messages via push from the server. No conversation ID needed. Legacy conv-id form still works.

- `--idle-timeout N` — exit after N seconds with no new messages (default 120; `0` disables).
- `--identity X` — override cwd-derived identity.

Exits cleanly (code 0) on idle; non-zero on socket error.

Example:
```bash
$ broker follow --idle-timeout 60
2026-04-22T10:15:03Z [proposit-server] READY: shared v1.2.3 published
2026-04-22T10:15:47Z [proposit-server → you, @proposit_core] QUESTION: who owns the migration?
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
$ broker history --from orchestrator --since 2026-04-22T09:00:00Z
2026-04-22T09:45:10Z [orchestrator → you] catch up on #1234 when you're free
```

### read — drain new lines, advance cursor

```
broker read [--identity <me>]
```

Print only inbox lines newer than the stored cursor, then advance the cursor to the end. Useful in scripted one-shots where you explicitly want to consume-and-mark. Legacy conv-id form still works for old callers.

Example:
```bash
$ broker read
2026-04-22T10:15:47Z [proposit-server → you, @proposit_core] QUESTION: who owns the migration?
```

**Do not chain `read` → `follow`.** Read advances the cursor, so follow will see nothing until the next new message. Use `follow` alone; it handles drain + stream.

## Legacy room commands

`broker create`, `join`, `leave`, `close`, `list`, `members` remain for backward compatibility but print deprecation warnings on stderr. They operate on the old `conversations/` store. New work should use the DM commands above — see `SKILL.md` for replacement patterns (side conversations become targeted `send --to` threads; "list" becomes `history`).
