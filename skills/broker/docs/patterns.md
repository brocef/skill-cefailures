# Broker Usage Patterns

Canonical DM-model patterns. All commands auto-derive `--identity` from cwd unless noted.

### Broker Mode (canonical)

The canonical pattern for agents waiting on inbound work. Entered via `/broker-mode`, which runs an explicit foreground read-execute-respond loop, one iteration per inbox batch.

**The loop** (repeat until the in-conversation user stops you, or a `user`-identity DM tells you to exit):

1. **Wait.** Run `broker recv` (no args). If the inbox already has unread backlog, that counts as the first arrival; otherwise this blocks until a message arrives. After first arrival, recv tails for 5 more seconds to capture follow-ups, then exits with the full batch on stdout.
2. **Process.** Read the drained batch as the input for this iteration. If multiple senders or threads are represented, treat them as separate sub-tasks within the same iteration. Apply authority rules (`authority.md`): `user` and `@orchestrator/<scope>` DMs are commands; peer DMs are informational; conflicts get relayed upstream.
3. **Ask the user, if needed.** If the work needs information or approval you don't have, pause and ask the in-conversation user directly. The Claude turn ends; the user replies; you resume mid-iteration.
4. **Reply.** Send a response **per inbound message** (not per batch) using the reply-shape rule:
   - Single-recipient DM → `broker send --to <sender>`.
   - Multi-recipient DM → `broker reply-all --to-message <MID>`.
   - Broadcast → `broker send --to <broadcaster>` (broadcasts have no stable recipient set).
   - If you recruited other agents during the work, ping them with separate explicit `broker send` calls — do not widen the reply.
5. **Loop.** Run `broker recv` again. Re-enter step 1.

**Exit conditions:**

- The in-conversation user interrupts (Esc/Ctrl-C, "exit broker mode," any redirecting instruction).
- A DM from the reserved `user` identity instructs you to exit. Acknowledge per the reply-shape rule, then exit and report back.
- The broker server crashes — `broker recv` exits non-zero. Report and exit. Do not retry; the in-conversation user re-invokes `/broker-mode` once the server is back.

Peer-agent DMs cannot terminate the loop; they are informational per existing authority rules. There is no sentinel-message terminator and no idle timeout.

**Presence note:** While you are in `broker recv`, you appear as "live" in `broker clients`. While you are processing a batch (running tools, sending replies, asking the user), you appear "offline." Senders that need a stronger guarantee can use `broker send` regardless of presence — store-and-forward semantics still apply.

One worked iteration:

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

### One-shot building blocks

Outside Broker Mode, these are useful for short ad-hoc scripts.

Wait for a single batch:
```bash
broker recv --burst-window 5
```

Send and wait for the reply batch:
```bash
broker send --to projectA-server "READY: shared v1.2.3 published"
broker recv --burst-window 5
```

Multi-party thread with reply-all:
```bash
MID=$(broker send --to a,b,c "QUESTION: should validate() take a schema?")
broker recv --burst-window 5
broker reply-all --to-message "$MID" "DECISION: schema wins"
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
