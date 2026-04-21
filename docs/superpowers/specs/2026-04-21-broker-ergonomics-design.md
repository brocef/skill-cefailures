# Broker Ergonomics Design

**Date:** 2026-04-21
**Scope:** Agent-ergonomics improvements to the broker CLI + skill. Does not cover DMs or addressable messages (those are simulated via conversation-naming conventions instead).

## Background

The broker is a chatroom-style CLI that lets multiple Claude Code agents and a human coordinate through a shared server over a Unix domain socket. Conversations persist to `~/.mcp-broker/conversations/` as JSON and are auditable after the fact.

In multi-agent runs observed during phase-1 work, every agent independently wrote the same unsafe polling loop in Bash:

```bash
while true; do
  result=$(broker read --identity <name> <cid> 2>/dev/null || echo '{"messages":[]}')
  echo "$result" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for m in d.get('messages', []):
  print(f\"[{m.get('sender','?')}] {m.get('content','')}\", flush=True)
"
  sleep 10
done
```

Some agents also maintained `/tmp/broker_<cid>_seen.txt` files to dedup messages across polls.

Both are wasted effort. The broker server already:

- Pushes new messages to every connected member's socket the moment a `send_message` lands (`broker_server.py:176-179`).
- Tracks per-identity read cursors server-side — `broker read` returns `messages[cursor:]` and advances the cursor (`broker_server.py:183-199`), so the same message is never returned twice to the same identity.

The push infrastructure is fully built on both sides (server + client library) but latent — the CLI doesn't expose it.

A separate pre-existing bug amplifies the problem: `BrokerServer.disconnect` (`broker_server.py:54-60`) wipes every conversation's membership and broadcasts `{identity} left` system messages. Every `broker send` / `broker read` cycle connects, does its thing, and disconnects — producing join/leave spam. A real transcript at `~/.mcp-broker/conversations/c20713.json` shows **35 of 47 messages (74%) are system join/leave noise**.

## Requirements

These three constraints, lifted from the user, govern every design decision in this document:

1. **Minimize agent token usage.** Push non-AI work to executables. Prefer compact line-based output over JSON for anything an agent reads. Avoid surfacing messages the agent doesn't need.
2. **Preserve on-disk persistence.** All transcripts stay in `~/.mcp-broker/conversations/` and remain auditable.
3. **The broker skill should carry richer usage guidance**, including subskills/docs. Agents should not need to invent polling loops, dedup hacks, or message-parsing scripts.

## Non-goals (explicitly deferred)

- **Protocol-level DMs or addressable messages.** Side conversations between two agents are simulated by creating a fresh conversation named `{a}-{b}-{topic}-{ts}` that other agents are instructed not to join. If DMs prove insufficient after this work lands, they become their own spec.
- **Claude Code hook-based message injection.** Exploratory option discussed and discarded — the observed agent workflow is explicit-wait-for-reply, not idle-interruption. Hooks don't fit turn-taking coordination.
- **Orchestrator-role rules.** Those stay in the user's workspace `CLAUDE.md`. The broker skill is role-agnostic.
- **Retroactive rewriting of existing transcripts** to strip old join/leave spam. Leave historical records intact; just stop generating new spam.

## Design

### Overview

Three tracks, all scoped to land together:

1. **CLI:** one new subcommand (`broker follow`), a compact output format, and a default filter on `broker list`.
2. **Server:** fix the disconnect-wipes-membership bug; shift the default of `list_conversations` to filter to `open`.
3. **Skill:** rewrite SKILL.md's Quick Reference + Critical Rules and add three new docs (`patterns.md`, `signals.md`, `troubleshooting.md`) using progressive disclosure.

### Track 1: CLI changes (`scripts/broker_cli.py`)

**New subcommand: `broker follow`**

```
broker follow <conversation_id> --identity <name>
  [--idle-timeout N]   # exit after N seconds of silence (default: 120)
  [--timeout N]        # hard cap in seconds (default: 600)
  [--count N]          # exit after N messages received (default: unset)
  [--include-system]   # include join/leave events (default: suppressed)
  [--format compact|json]  # compact is default
```

Behavior:

1. Connect to the broker socket.
2. Call the existing `history` request to drain any unread backlog; print each message to stdout in the requested format.
3. Consume push messages from the existing client-side `on_push` queue (`broker_client.py:53-74`); print each to stdout.
4. Exit when any of these becomes true: idle-timeout elapses since the last received message, total timeout reached, or count messages received.
5. On socket disconnect mid-stream, print a single-line error to stderr and exit non-zero. No silent hangs.

Compact output format (one message per line, no quoting):

```
[server] Okay, on it
[core] Ready for the issue description
```

System messages are suppressed in compact output unless `--include-system` is passed. When included, they render as `[system] {identity} joined` / `[system] {identity} left`.

**Updated subcommand: `broker list`**

Default changes from "all" to "open only." To restore the previous behavior:

```
broker list                   # open conversations only (new default)
broker list --status open     # explicit, equivalent to no flag
broker list --status closed   # closed only
broker list --status all      # everything (previous default)
```

Rationale: matches the "closed conversations drop out of the agent's working view but stay on disk for audit" principle.

**Format flag on `broker read`**

`broker read --format compact` emits the same `[sender] content` lines `follow` uses. Default remains JSON to preserve back-compat for any existing script that parses it. Included in scope: the compact formatter is a pure function of a message list, so reusing it between `follow` and `read` is trivial and gives agents one format to reason about across both commands.

**Unchanged:** `create`, `send`, `join`, `leave`, `members`, `close`, `server`, `repl`.

### Track 2: Server changes (`scripts/broker_server.py`)

**Fix `BrokerServer.disconnect` (membership bug).**

Current:

```python
def disconnect(self, identity: str) -> None:
    self.clients.pop(identity, None)
    for cid, member_set in list(self.members.items()):
        if identity in member_set:
            member_set.discard(identity)
            self._broadcast_system(cid, "leave", identity)
```

New:

```python
def disconnect(self, identity: str) -> None:
    """Remove a client socket. Does not change conversation membership."""
    self.clients.pop(identity, None)
```

Membership now changes only via explicit `join`, `leave`, and `close` handlers (no changes to those). `send`'s auto-join remains — a new sender becomes a member on first send, and `_join_member`'s existing "already a member" guard keeps re-sends quiet.

**Historical data is not rewritten.** Existing on-disk JSONs keep their historical join/leave messages intact; new sessions simply stop producing them.

**Shift `_handle_list` default.**

```python
def _handle_list(self, identity: str, msg: dict) -> dict:
    status_filter = msg.get("status", "open")  # was: no default
    ...
    if status_filter != "all":
        if status_filter and conv["status"] != status_filter:
            continue
    ...
```

`"all"` is a new accepted value that means "no filter." Absence of `status` means `"open"`.

**Other server changes:** none. Push, cursor, persistence, and REPL all untouched.

### Track 3: Skill restructure (`skills/broker/`)

**Structure:**

```
skills/broker/
  SKILL.md                  # updated
  docs/
    setup.md                # minor update for new defaults
    usage.md                # updated: adds follow, compact format, new list default
    patterns.md             # NEW
    signals.md              # NEW
    troubleshooting.md      # NEW
```

**SKILL.md — Quick Reference table gains:**

| Command | Description |
|---------|-------------|
| `broker follow CID --identity NAME` | Block until messages arrive; print compact lines; exit on idle. |

**SKILL.md — new Critical Rules section (inlined, not routed to a doc):**

- Use `broker follow` to wait for messages. Do not write a `while true; broker read; sleep N` loop.
- Do not parse broker output with `python`, `jq`, or similar. The compact line format is the agent-facing format.
- Do not maintain `/tmp/*_seen.txt` dedup files. The server tracks per-identity cursors.
- For focused 2-agent discussions, create a new conversation named `{a}-{b}-{topic}-{ts}` instead of using a shared room.

**New `docs/patterns.md`** — canonical usage patterns:

- Wait-for-reply snippet (`broker send` + `broker follow --idle-timeout`).
- Side-conversation pattern: when to fork a room, naming, invite/exclude conventions, lifecycle, closing when done.
- Main-room-vs-side-room decision rule: short signals stay in main; deep dives fork.
- Stream-while-working pattern (Monitor-backed `broker follow` for the rarer case where the agent has other work and wants message notifications alongside).

**New `docs/signals.md`** — the READY / BLOCKED / QUESTION / DECISION vocabulary as sensible defaults for any broker-using project. Short and prescriptive: what each signal means, when to use it, format. A project `CLAUDE.md` can override.

**New `docs/troubleshooting.md`** — anti-patterns and why they're wrong. Each entry is structured:

- What the agent tried.
- Why it's wrong (with a reference to the underlying mechanism — cursor, push, etc.).
- What to do instead.

Seeded with the specific failures from the phase-1 transcript:
- `while true; broker read; sleep N` loop.
- `python3 -c "..." ` JSON parsing.
- `/tmp/broker_*_seen.txt` dedup files.
- `2>/dev/null || echo '{"messages":[]}'` error swallowing.

### Track 4: Testing

- New `tests/test_broker_follow.py`:
  - Drain-backlog-then-exit on idle.
  - Push message arrives during follow → printed.
  - `--count N` exits after N messages.
  - `--timeout N` hard cap.
  - `--include-system` toggles join/leave rendering.
  - Graceful disconnect → non-zero exit with stderr message.
- Update existing tests that asserted leave-on-disconnect behavior to assert the opposite (membership persists across disconnect).
- No tests for skill-doc content.

### Track 5: Rollout

- Per this repo's CLAUDE.md: bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. Proposed bump: `minor` (new feature: `broker follow` + structural skill expansion).
- Rename `docs/release-notes/upcoming.md` → `docs/release-notes/v{version}.md` and `docs/changelogs/upcoming.md` → `docs/changelogs/v{version}.md`. Start fresh `upcoming.md` files.
- After version commit, tag `v{version}`.
- No commit co-author trailers.

## Back-compat summary

| Change | Back-compat impact |
|---|---|
| `broker follow` subcommand | Additive. |
| `broker list` default = `open` | Minor behavior change; `--status all` restores previous default. |
| Compact output format on `follow` | New code path. `read` still emits JSON by default. |
| Disconnect bug fix | Bug fix. No consumer depended on the spam. |
| New skill docs | Additive. |

## Open questions

None at time of writing. If the implementation surfaces any, they will come back through writing-plans.

## Success criteria

- An agent asked to wait for a reply runs exactly one CLI command — `broker follow` — and never writes a polling loop, a JSON parser, or a dedup file.
- Fresh conversation transcripts (post-deploy) do not accumulate join/leave spam across agent runs.
- `broker list` returns only open conversations by default.
- The skill's SKILL.md is short enough to stay cheap to load but contains all rules an agent needs to avoid the observed anti-patterns before consulting detailed docs.
