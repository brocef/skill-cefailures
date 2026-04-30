# Broker DM-only redesign — design

**Date:** 2026-04-22
**Status:** Design proposal
**Source material:** `/Users/brian/Projects/Proposit-App/broker-feedback.md` — friction observed during a Phase 1 orchestration session (2026-04-22) coordinating four per-repo Claude Code agents over the current room-based broker.

---

## Summary

Replace the broker's room-based model (conversations with members + topics, create/join/leave/close lifecycle) with a pure direct-messaging model: each identity has a persistent inbox; senders address specific recipients; `follow` streams all incoming messages regardless of origin; `broadcast` fans out to every registered identity. Store-and-forward semantics mean recipients don't need to be online at send time.

The simplification absorbs every pattern the current model supports (1:1 DM, multi-party, hub-and-spoke, lobby/broadcast) and retires the room abstraction that caused most of the observed friction.

## Motivation

A single-session orchestration exercise generated 11 rooms across 4 agents, required one topology migration mid-stream (per-sub-project rooms → per-agent durable DM rooms), and surfaced one observable "lockup" that was root-caused to orchestrator-side relay lag rather than any broker defect. Underlying the friction:

- **Room topology requires design.** "Where should this message go?" is a recurring decision agents and orchestrators have to make. Each new initiative tempts more rooms.
- **`broker follow` is single-room.** A hub participant (orchestrator) watching N rooms needs N background follows, and `Bash(run_in_background: true)` yields only completion notifications, not per-message pushes.
- **Read cursors hide history** without a `--from-start` escape hatch.
- **Close doesn't evict members** — cosmetic but surprising.
- **Presence vs. membership invisible** — can't distinguish an actively-following agent from a dead session.
- **Identity migration unsupported** — `proposit-shared` vs. `shared` remain separate members with no alias.
- **Bootstrap notification problem** — agent A creating a room can't tell agent B that it exists unless they share a prior channel.

Most of these collapse in a DM-only model because there's no room abstraction to manage.

## Core model

### Identities

An identity is a string, globally unique within a broker server instance.

**Reserved identities** (normal agents cannot register these):

- `orchestrator` — workspace-level coordinator role.
- `human` — the human operator.

**Normal agent identity derivation** (required, enforced at registration):

1. If the agent's working directory contains a `package.json`, the identity is that file's `name` field verbatim. Examples: `@proposit/shared`, `@proposit/proposit-core`, `proposit-server`, `proposit-mobile`.
2. Otherwise the identity is the full `<org>/<repo>` GitHub-style reference. Example: `Proposit-App/proposit-mobile`.
3. Normalization: case-insensitive lookup. Broker stores the canonical form as provided; matches case-insensitively.

Rationale: deterministic identity derivation solves the "how do I address X?" problem without a discovery protocol or a central directory. Anyone can compute the recipient's identity from the recipient's project.

### Inboxes (store-and-forward)

Each identity has a persistent inbox backed by durable storage. The broker accepts sends at any time regardless of the recipient's connection state, queuing messages in the recipient's inbox. When an identity connects and `follow`s, they drain queued messages first (in timestamp order) and then stream live pushes.

**Delivery semantics:** at-least-once. Agents are expected to be idempotent on message IDs.

**Retention:** forever by default. Policy-configurable expiry (e.g., 90 days) for deployments that need to bound storage.

## Commands

### `send`

```
broker send --identity <from> --to <recipient[,recipient...]> <content>
```

Delivers `<content>` to each specified recipient's inbox. Single-recipient is the common case; multi-recipient enables group chats and reply-all.

- Rejects if `<from>` is a reserved identity and the caller is an unprivileged agent.
- Rejects if `<recipient>` is `BROADCAST` — use the `broadcast` command.
- Accepts any mix of registered identities as recipients.

### `broadcast`

```
broker broadcast --identity <from> <content>
```

Delivers `<content>` to every registered identity's inbox. One-way fan-out; broadcasts are not replyable (see `reply-all`). Normal DMs initiated back to the broadcaster are of course always allowed; "not replyable" means there is no reply-all primitive bound to a broadcast.

### `reply-all`

```
broker reply-all --identity <from> --to-message <message-id> <content>
```

Looks up the original message by ID and computes the reply recipient set:

- If the original was a normal `send`: recipient set = `[original-sender] + original-to-list − self`. Email convention — no self-echo.
- If the original was a `broadcast`: CLI rejects the invocation. To respond to a broadcaster, use `send --to <broadcaster>`.

### `follow`

```
broker follow --identity <name>
```

Blocks, drains the identity's inbox (in timestamp order, catching up on any messages received while offline), then streams live pushes as they arrive. Exits on idle-timeout, count, close signal, or SIGINT.

This is the active-listener primitive. One invocation covers both catch-up and go-forward; do not precede it with a `read` (that would consume the cursor ahead of the follow).

### `history`

```
broker history --identity <name> [--from <identity>] [--since <iso8601>] [--with-ids]
```

Reads the inbox without advancing the read cursor. Filters optional. `--with-ids` includes message IDs in the output (needed for `reply-all`). Distinct from `read`, which advances the cursor.

### `read`

```
broker read --identity <name> [--format compact|json]
```

Returns messages since the identity's last read cursor, advances the cursor. Retained for scripted catch-up where `follow` would be overkill. For typical active listening, prefer `follow`.

## Message format

All display paths (`follow`, `history`, `read`) use a single line-oriented format:

```
<ISO8601> [<sender>] <content>                              # DM to you (you are the sole recipient)
<ISO8601> [<sender> → <recipient>,<recipient>] <content>    # multi-recipient; you are one of them
<ISO8601> [<sender> → BROADCAST] <content>                  # broadcast; not replyable
```

### Grammar

```
message        ::= <timestamp> <SP> "[" <meta> "]" <SP> <content>
timestamp      ::= ISO 8601 UTC, e.g. 2026-04-22T17:30:00Z
meta           ::= <sender> [ <SP> "→" <SP> <recipient-list> ]
recipient-list ::= "BROADCAST" | <identity> { "," <SP> <identity> }
content        ::= arbitrary text to end of line
```

When the receiver is the sole recipient, the arrow + recipient list is omitted (no `→ you` noise — the inbox context already implies it). When multi-recipient, the receiver appears in the list as their own identity (e.g., `→ you, proposit-server` from mobile's perspective, or the literal identity `proposit-mobile → @proposit/shared, proposit-mobile` from shared's). The `you` placeholder is optional; concrete identities are always valid.

### Parser

```
^(\S+)\s+\[([^\]]+)\]\s+(.*)$
```

Group 1 = timestamp, group 2 = metadata, group 3 = content. Split metadata on ` → ` to get sender and (optional) recipient list. Check recipient list literal for `BROADCAST` to distinguish message type.

### Example stream

```
2026-04-22T17:30:00Z [@proposit/shared] 0.3.0 types final; publishing in 10
2026-04-22T17:31:12Z [@proposit/shared → BROADCAST] publishing now, bump ^0.3.0 when ready
2026-04-22T17:33:48Z [proposit-mobile → you, proposit-server] bumped to 0.3.0 on phase-1/pr-1c-auth, CI green
2026-04-22T17:34:05Z [orchestrator] thanks, ack'd
```

## Impact on the v1 friction list

| v1 issue | Outcome in DM-only model |
|---|---|
| #1 Dropped messages via orchestrator lag | Resolved. Orchestrator watches exactly one inbox (its own); no cross-room polling. |
| #2 `broker follow` is single-room | Resolved. One inbox per identity; `follow` streams everything destined for you. |
| #3 Read cursors obscure history | Resolved. `broker history` reads without moving the cursor; first-class. |
| #4 `run_in_background` doesn't push per-message | Much cheaper. A single `follow` stream paired with Claude Code's `Monitor` tool (file-line streaming) gives per-message push delivery. |
| #5 Close doesn't evict members | N/A. No rooms, no members. |
| #6 Presence vs. membership invisible | Still needs addressing but no longer critical. Can add `broker whois <identity>` surfacing `lastConnectedAt` / `lastReadCursor`. |
| #7 Identity migration unsupported | Partially resolved. Package-name-derived identities reduce ad-hoc identity choices, so migrations are rarer. A proper `broker identity rename <old> <new>` is still a future add. |
| #8 Topology changes need batch primitives | N/A. No topology to migrate. |
| #9 Broker server health implicit | Unchanged; `broker status` is still a good add. |
| #10 Skill docs: `read` before `follow` desyncs | Clearer. `follow` is the active listener (drain + stream); `history` is the cursor-free peek; `read` retained for scripted catch-up with explicit cursor advancement. |

## Design considerations

### Group-chat thread continuity

Without a room-scoped topic, "group chats" persist only as long as replying parties preserve the original recipient list. Drift to smaller subsets is allowed — someone replies-all minus one recipient, effectively forking the thread. This mirrors email group threads: a feature, not a bug, and agents reason about it the same way humans do in email.

If sub-setting a multi-party thread ever proves to be a problem, an optional thread-id header could be added to messages. Not planned for v1 of the DM model.

### Signal prefixes

The content-level convention (`READY:` / `BLOCKED:` / `DECISION:` / `QUESTION:`) is orthogonal to transport and unchanged by this redesign. Agents still prefix coordination messages; the orchestrator still pattern-matches on prefixes for routing decisions — just now inside a single DM stream instead of across rooms.

### Message IDs

Short, human-readable, monotonic-ish identifiers (current scheme — `msg-a1b2c3` — is fine). Not included in the default display format because they clutter. Exposed via `broker history --with-ids` for `reply-all` and debugging.

### Broadcast semantics

Broadcasts are one-way. Replying to a broadcast sender is always possible via `send --to <broadcaster>` — a normal DM, not a reply. The distinction is that `reply-all` does not operate on broadcasts because there is no meaningful reply-all recipient set (the original "recipient list" is the set of all registered identities, and that set changes over time).

### Reserved identities and CLI enforcement

`orchestrator` and `human` are server-enforced reserved identities. Registration attempts by other callers fail. The CLI must also enforce that normal agents cannot spoof these identities in `--identity` of `send` / `broadcast` / `follow` — the broker server verifies the caller's auth (e.g., Unix socket peer UID, or per-identity token) against the identity they claim.

### Privacy

All messages land in the named recipient's inbox. The broker does not route messages through unrelated identities. Broadcast messages go to every identity but are clearly marked as broadcast.

## Open questions

- **Identity auth.** The current broker is local-Unix-socket; authentication is implicit (any local user can impersonate any identity). That's fine for single-user dev use but would need shoring up if broker goes cross-user or remote. Out of scope for this design.
- **Retention policy mechanics.** Is expiry per-message (TTL) or per-inbox (keep last N)? Initial proposal: per-message TTL, configurable per deployment, unset by default.
- **Offline send quotas.** If a sender blasts 10k messages to an offline identity, does the broker rate-limit or backpressure? Initial stance: accept all, rely on retention policy to bound storage.
- **Delivery confirmations.** Does `send` return a message ID and a per-recipient delivery receipt? Proposal: yes — `send` returns `{ messageId, delivered: [identity...] }` where `delivered` lists identities that were online at send-time (received a push) vs. `queued` identities whose inboxes hold the message pending their next connection.

## Migration path from v1

1. **Broker server** adds store-and-forward inbox model alongside the existing room model. Both operate in parallel during transition. Room APIs continue to work; `send` / `broadcast` / `follow` (without a `--conv` arg) introduce the inbox paths.
2. **Skill** (`skill-cefailures:broker`) is updated with dual-mode docs. New CLAUDE.md conventions (in consumer projects) reference the DM model.
3. **Consumer projects** (e.g., Proposit-App) update their CLAUDE.md `## Broker coordination` sections. Agents re-register under package-name-derived identities.
4. **Existing rooms** are drained by their participants and closed. No new rooms created.
5. **Broker server** deprecates the room API (return error on `create` / `join`; `follow --conv <id>` becomes a no-op or alias to the inbox stream).
6. **Next major broker version** removes room-based APIs entirely.

## What this proposal does not change

- Signal prefixes (`READY:` / `BLOCKED:` / `DECISION:` / `QUESTION:`) — content convention, unaffected.
- Durable JSON persistence under `~/.mcp-broker/` — storage shape becomes per-identity instead of per-conversation, but the idea is unchanged.
- The skill's usage patterns (agents still send, listen, and coordinate). Mental model simplifies: "send messages, listen on your inbox" instead of "find the right room, manage its lifecycle, etc."
