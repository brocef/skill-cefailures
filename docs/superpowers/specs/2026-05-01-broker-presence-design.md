# Broker Presence: Socketed `follow` for Accurate `who`

**Date:** 2026-05-01
**Status:** Approved for planning

## Problem

`broker follow` is currently a pure file-tailer. It reads `~/.mcp-broker/inbox/<identity>.log` directly off disk on a 200ms loop and never opens a socket to the broker server. As a consequence:

- `BrokerServer.clients` (the in-memory map of live socket connections) does not include followers.
- The REPL `who` command and the `broker clients` subcommand both render `self.clients.keys()`, so they always report `(no clients connected)` even when many agents are actively listening.
- Followers have no way to detect that the server has stopped; they keep tailing files silently.

The user-facing contract for `who` / `broker clients` is "list all agents listening for messages." The current implementation does not satisfy that contract.

## Goals

1. `who` and `broker clients` accurately reflect agents listening via `broker follow`.
2. Followers receive a clear signal when the broker server stops.
3. Inbox delivery semantics are unchanged — store-and-forward, file-based backlog, and cursor advancement continue to work as today.
4. The output of `who` answers "who is listening right now" *and* "who is known but offline" in one view.

## Non-goals

- Replacing file-based delivery with socket pushes. The on-disk inbox log remains the source of truth for message delivery; the socket is purely a presence beacon.
- Authenticating identities. The reserved-identity convention is unchanged.
- Heartbeats, presence-across-server-restart, or any new on-disk presence mechanism.

## Design

### Connection model

`broker follow` opens a long-lived `BrokerClient` connection to the broker server and holds it for the lifetime of the follow session. The socket carries no inbox traffic — message delivery continues to come from tailing the per-identity inbox log file. The open socket is the agent's presence beacon: open = listening, closed = gone.

The connect-message wire protocol gains a `mode` field:

```json
{ "type": "connect", "identity": "@org/proj", "mode": "follow" }
```

Valid values are `"follow"` and `"oneshot"`. The server tracks two maps with distinct purposes:

- `BrokerServer.clients: dict[str, Callable]` (existing) — any open socket where we *might* push `inbox_message` events. Both follow and oneshot connections register here. This is what the existing `_handle_send_dm` and `_handle_broadcast` push paths key on; the in-process REPL relies on this for its `<-` notifications, and we must not break that path.
- `BrokerServer.followers: dict[str, FollowerHandle]` (new) — presence registry. Only `mode == "follow"` connections register here. Drives `who` / `broker clients` output and the "one follower per identity" rule.

A `mode == "follow"` connect adds to **both** maps. A `mode == "oneshot"` connect adds to `self.clients` only. Disconnect removes from both.

Pushing `inbox_message` events to socketed followers is harmless: `BrokerClient` in follow mode does not set its `on_push` queue, so `_listen` silently discards the push (line 64 of `broker_client.py`). Delivery for socket followers continues to come from tailing the inbox log file. We could optimize later by skipping pushes to follow-mode entries, but it's not needed for correctness.

### Reject second follower for same identity

If a `connect` arrives with `mode == "follow"` for an identity already present in `self.followers`, the server returns:

```json
{ "type": "error", "id": "...", "message": "identity '@org/proj' already has an active follower" }
```

The second follower exits with this error printed to stderr. Oneshot connects from the same identity during an active follow are allowed and unaffected — they don't trip the reject rule, since they go to `self.clients`, not `self.followers`.

Rationale: two followers for the same identity in the same workspace is almost always a configuration mistake (two terminals derive the same cwd-based identity). Failing fast surfaces it immediately.

### `list_clients` payload

The REPL `who` command and the `broker clients` subcommand both call the existing `list_clients` request. The response payload changes from:

```json
{ "clients": ["@a/x", "@b/y"] }
```

to:

```json
{
  "live": [
    { "identity": "@a/x", "mode": "follow", "since": "2026-05-01T15:30:12Z" }
  ],
  "offline": [
    { "identity": "@a/y", "lastSeenAt": "2026-04-29T10:00:00Z", "lastWriteAt": "2026-04-29T10:00:00Z" }
  ]
}
```

- `live` is sourced from `self.followers` (sorted by identity). `mode` is included for forward compatibility — today the only live listing source is followers. `since` is the ISO8601 timestamp the *current* socket connected; a reconnect resets it.
- `offline` is sourced from `IdentityRegistry.all()` minus identities currently in `live`, sorted by identity. The `live`/`offline` set difference must be case-insensitive: `IdentityRegistry` keys identities by `lower()` (`broker_storage.py:135`) and returns canonical-cased names from `.all()` (line 154), while `self.followers` keys on whatever string the connect message provided. Compute the difference by lowercasing both sides; render `offline` using the registry's canonical form. `lastSeenAt` and `lastWriteAt` come from the existing registry entries.

The REPL renders this as:

```
broker> who
  @a/x       live, since 2026-05-01T15:30:12Z (you)
  @b/x       live, since 2026-05-01T15:31:04Z
  @a/y       offline, last seen 2026-04-29T10:00:00Z
  (no live followers, no registered identities)   # only when both lists are empty
```

The `(you)` marker continues to mark the REPL's own identity in the live list.

The `broker clients` subcommand renders the same human-readable view as the REPL `who` handler (see `scripts/broker_cli.py` notes below for the exact code path that needs rewriting).

### Follower lifecycle

1. **Start.** `cmd_follow_inbox` opens a `BrokerClient` and calls `connect(mode="follow")`.
   - On `ConnectionError` (server down): print the existing "Cannot connect to broker at … Is the broker server running?" message and exit non-zero. **This is a behavior change** — today, `follow` works without a server. The change is intentional: a follower that cannot register is not "listening" under the new presence semantics.
   - On `ValueError("identity '…' already has an active follower")`: print the error to stderr and exit non-zero.
2. **Steady state.** `cmd_follow_inbox` continues its existing 200ms file-tail loop. The socket is held open in the background but receives no application traffic. (`BrokerClient._listen` sees only the eventual EOF.)
3. **Server shutdown / crash mid-follow.** The socket reads EOF. Print `[broker] server disconnected` to stderr and exit non-zero. The agent layer decides whether to re-run.
4. **Abrupt follower death (`kill -9`).** The OS closes the socket. The server's existing `_handle_client` `finally` block calls `server.disconnect(identity)`, which now also removes the entry from `self.followers`. Presence drops correctly.

### Registry interaction

The existing `IdentityRegistry.touch(identity, now, wrote=False)` call inside `BrokerServer.connect` continues to fire on every connect — both follow and oneshot. We do **not** add a touch on disconnect: `lastSeenAt` keeps its existing semantics ("last connection event"). For an offline follower, `lastSeenAt` therefore reflects the time of their most recent connect, which is a reasonable proxy for "last seen" without introducing an asymmetric write path or noisy double-touches for short-lived oneshots. The `live` annotation in the new payload makes "currently active" obvious; `lastSeenAt` is only consumed for the `offline` view, where it answers "when did this identity last connect."

### Backwards compatibility

- The wire protocol's `connect` message gains an optional `mode` field. If absent, the server defaults to `"oneshot"`. Existing `BrokerClient.connect()` callers in tests or external scripts work unchanged.
- The `list_clients` response shape changes from `{"clients": [...]}` to `{"live": [...], "offline": [...]}`. The CLI and REPL ship in lockstep with the server, so this is a coordinated change. External consumers of the JSON shape (if any) must be updated.

## Components

### `scripts/broker_client.py`

- `BrokerClient.__init__` gains `mode: str = "oneshot"`.
- `BrokerClient.connect()` includes `"mode": self.mode` in the connect message.

### `scripts/broker_server.py`

- New attribute: `self.followers: dict[str, dict] = {}`. Each entry: `{"since": str}`. (The send callback already lives in `self.clients[identity]`; we don't duplicate it.)
- `BrokerServer.connect(identity, send, mode="oneshot", token=None)`:
  - If `mode == "follow"` and `identity in self.followers`: raise `ValueError("identity '<X>' already has an active follower")`.
  - Always: `self.clients[identity] = send` (existing behavior — supports the REPL's `_on_push` and any future socket-push consumers).
  - If `mode == "follow"`: also `self.followers[identity] = {"since": self._timestamp()}`.
  - Always: `self.registry.touch(identity, now=self._timestamp(), wrote=False)` (existing behavior, unchanged).
- `BrokerServer.disconnect(identity)` removes from both `self.clients` and `self.followers`. No registry touch on disconnect (see Registry interaction).
- `_handle_list_clients` returns the new `{live, offline}` payload as specified above.

### `scripts/broker_cli.py`

- `cmd_follow_inbox` opens a `BrokerClient(identity, sock_path, mode="follow")`, calls `connect()`, then enters the existing file-tail loop. Connect errors print to stderr and return non-zero. The connection is held alive by an asyncio loop running on a background `threading.Thread`; that thread watches for socket close and sets a `threading.Event` (`_socket_closed`) when EOF is observed. The synchronous file-tail loop checks this event each iteration (between `time.sleep(poll_interval)` calls) and exits non-zero with `[broker] server disconnected` to stderr if set.
- The REPL `who` handler renders the new payload (live first, then offline; both sorted by identity; `(you)` marker preserved on the REPL's own identity in `live`).
- The `broker clients` subcommand at `broker_cli.py:516-524` currently iterates `result.get("clients", [])` directly. It must be rewritten against the new `{live, offline}` payload, using the same rendering as the REPL `who` handler. (The reviewer flagged this as a concrete code path that breaks under the new shape if left untouched.)

### REPL

- `ServerREPL.__init__` continues to call `self.server.connect(identity, self._on_push)` directly. We update this call site to pass `mode="follow"` so the REPL appears in `live` with `(you)`. The REPL participates in the "one follower per identity" rule. **Foot-gun:** if a user runs `broker server --identity X` and then `broker follow` in another terminal where the cwd-derived identity also resolves to `X`, the second follower will be rejected. This is documented in failure modes and `troubleshooting.md`.

## Failure modes

| Scenario | Behavior |
|---|---|
| Server unreachable at `broker follow` start | Existing connect-error message; exit non-zero |
| Server dies mid-follow | Socket EOF → print `[broker] server disconnected` → exit non-zero |
| Second `broker follow` for the same identity | Server rejects with `ValueError`; CLI prints message; exit non-zero |
| Follower `kill -9`'d | OS closes socket → server `_handle_client` `finally` → `disconnect` cleans `self.followers` |
| Oneshot send during active follow (same identity) | Allowed; oneshot lands in `self.clients` only, not `self.followers`; `who` unaffected |
| `broker follow` from a workspace whose identity matches the running `broker server --identity X` | Server REPL is itself a follower for `X`, so the second follow is rejected. User-visible foot-gun; documented in troubleshooting. |

## Tests

### Server (`tests/test_broker_server.py`, or whatever the current path is)

- `connect(mode="follow")` populates `self.followers`, not just `self.clients`.
- Second `connect(mode="follow")` for the same identity raises `ValueError` with the documented message.
- `connect(mode="oneshot")` while a follow is active for the same identity succeeds.
- `disconnect(identity)` removes from both `self.clients` and `self.followers` and does *not* touch the registry (per the Registry interaction section).
- `list_clients` returns `{live: [...], offline: [...]}` with correct partitioning, sorted by identity, and includes `since` for live entries and `lastSeenAt` for offline entries.

### CLI (`tests/test_broker_cli.py`)

- `cmd_follow_inbox` exits non-zero with the connect-error message when the socket path doesn't exist.
- `cmd_follow_inbox` exits non-zero with the rejection message when a follower is already active for the identity.
- `cmd_follow_inbox` exits non-zero when the server closes the socket mid-session.
- `cmd_follow_inbox` continues delivering inbox lines via the file-tail loop while the socket is held open (delivery path unchanged).
- `broker clients` subcommand renders the new `{live, offline}` payload correctly: both lists empty → `(no live followers, no registered identities)`; live-only; offline-only; mixed.

### REPL / Integration

- REPL `who` shows the REPL itself as `live (you)`, plus any active followers as `live`, plus registered-but-disconnected identities as `offline`.
- `broker clients` subcommand returns the same data as JSON.

## Docs

- `skills/broker/SKILL.md` — `broker follow` description must mention that the server is required (load-bearing behavior change).
- `skills/broker/docs/setup.md` — note that `broker follow` now requires the server to be running.
- `skills/broker/docs/troubleshooting.md` — the existing "socket closed unexpectedly" entry becomes accurate; add a new entry for "identity already has an active follower."
- `skills/broker/docs/usage.md` — update the `who` / `broker clients` output examples to show the live/offline split.
- `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` — note the wire protocol change (`mode` field, `list_clients` payload shape) and the behavior change (`broker follow` now requires the server).

## Open questions

None.
