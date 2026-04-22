# Broker Usage Patterns

Canonical DM-model patterns. All commands auto-derive `--identity` from cwd unless noted.

### Wait for a reply

Send, then block on your inbox. `broker follow` drains any backlog and streams new arrivals; it returns when the conversation goes quiet.

```bash
broker send --to proposit-server "QUESTION: which schema version for v1.3?"
broker follow --idle-timeout 120
```

Tune `--idle-timeout` to your patience: 60s for a quick ping, 600s (or `0` to disable) if the other agent is doing real work.

### Announce to everyone

Use `broadcast` for state changes that every registered agent should see — CI breakage, registry outages, big milestones.

```bash
broker broadcast "BLOCKED: npm registry is down, pausing publishes"
```

Pitfall: broadcasts have no stable recipient set. Don't try to `reply-all` to one — DM the broadcaster directly: `broker send --to <broadcaster> "…"`.

### Multi-party thread with reply-all

Capture the message ID from `send`, then use `reply-all` to address the same group without retyping `--to`. Reply-all automatically excludes yourself.

```bash
MID=$(broker send --to proposit-server,proposit-core "QUESTION: validate(schema) or validate(obj)?")
broker follow --idle-timeout 180
broker reply-all --to-message "$MID" "DECISION: validate(schema) wins; shared will expose the type."
```

Pitfall: `reply-all --to-message` on a broadcast errors. If the thread started with a broadcast, fall back to explicit `send --to`.

### Catch up after being away

`broker history` reads the inbox without moving the cursor — use it for situational awareness. `broker read` drains new lines and advances the cursor — use it when you want the lines out of your backlog permanently.

```bash
broker history --since 2026-04-22T09:00:00Z        # browse recent traffic, no side effects
broker history --from orchestrator                  # just orchestrator's DMs to you
broker read                                         # consume new, advance cursor
```

When in doubt, prefer `broker follow` over `broker read`: follow drains into your context and then streams, which is almost always what you want.

### Orchestrator watching many agents

An orchestrator's inbox is the union of every DM addressed to it — `send --to orchestrator`, `reply-all` threads that include it, and broadcasts. A single `broker follow` on the orchestrator's own inbox captures every relay. No multi-room follow; no fan-in bookkeeping.

```bash
# In the orchestrator's workspace
broker follow --idle-timeout 0        # stream indefinitely; Monitor/Ctrl-C when done
```

### Streaming into Claude Code's `Monitor` tool

Point `Monitor` directly at the per-identity inbox log to push each new message into your context as it's written. Useful for orchestrators that want per-message reactivity without holding a blocking `broker follow` in the foreground.

```bash
# Example path — replace with the output of `broker whoami | sed 's#/#_#g'`
~/.mcp-broker/inbox/orchestrator.log
```

Each appended line becomes a Monitor notification. Pair with `broker history` if you need to also read the backlog before streaming.

Pitfall: every streamed line consumes context. Prefer foreground `broker follow` when you're explicitly waiting; reserve Monitor streaming for orchestrators and long-lived coordinators.

## Anti-patterns

See `troubleshooting.md`. If you're about to write a bash loop or a jq pipeline, read that doc first.
