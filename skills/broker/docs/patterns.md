# Broker Usage Patterns

Canonical DM-model patterns. All commands auto-derive `--identity` from cwd unless noted.

### Broker Mode (canonical)

The canonical pattern for agents waiting on inbound work. Entered via `/broker-mode`. See `SKILL.md`'s "Broker Mode" section for the full loop. One worked iteration:

```bash
# Step 1 — wait for a batch.
$ broker recv
2026-04-22T10:15:03Z [projectA-server] QUESTION: which schema version for v1.3?

# Step 2 — process. (Agent does work. May ask the in-conversation user.)

# Step 3 — reply per the shape rule. Single-recipient DM → send --to sender.
$ broker send --to projectA-server "DECISION: v1.3.0; shared exposes the type."
msg-e9d201

# Step 4 — loop.
$ broker recv
...
```

### Announce to everyone

Use `broadcast` for state changes that every registered agent should see — CI breakage, registry outages, big milestones.

```bash
broker broadcast "BLOCKED: npm registry is down, pausing publishes"
```

Pitfall: broadcasts have no stable recipient set. Don't try to `reply-all` to one — DM the broadcaster directly: `broker send --to <broadcaster> "…"`.

### Multi-party thread with reply-all

Capture the message ID from `send`, then use `reply-all` to address the same group without retyping `--to`. Reply-all automatically excludes yourself.

```bash
MID=$(broker send --to projectA-server,projectB-core "QUESTION: validate(schema) or validate(obj)?")
broker recv --burst-window 5
broker reply-all --to-message "$MID" "DECISION: validate(schema) wins; shared will expose the type."
```

Pitfall: `reply-all --to-message` on a broadcast errors. If the thread started with a broadcast, fall back to explicit `send --to`.

### Catch up after being away

`broker history` reads the inbox without moving the cursor — use it for situational awareness. `broker read` drains new lines and advances the cursor — use it when you want the lines out of your backlog permanently.

```bash
broker history --since 2026-04-22T09:00:00Z        # browse recent traffic, no side effects
broker history --from @orchestrator/myorg              # just orchestrator's DMs to you
broker read                                         # consume new, advance cursor
```

When in doubt, prefer `broker recv` over `broker read`: `recv` drains backlog into your context and then waits for the next batch, which is almost always what you want.

### Orchestrator watching many agents

An orchestrator runs Broker Mode just like any other agent. The `@orchestrator/<scope>` inbox is the union of every DM addressed to it — `send --to @orchestrator/<scope>`, `reply-all` threads that include it, and broadcasts. A single `broker recv` per iteration drains the next batch; the orchestrator decides which messages to relay or act on, and replies per the shape rule. There is no fan-in bookkeeping and no background streaming; the orchestrator is just an agent that relays rather than implements.

## Anti-patterns

See `troubleshooting.md`. If you're about to write a bash loop or a jq pipeline, read that doc first.
