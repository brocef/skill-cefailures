# Broker Mode — design

**Date:** 2026-05-01
**Status:** Design proposal
**Source material:** Brainstorming session 2026-05-01; prior feedback memory on broker design requirements (token-minimal, on-disk persistent, skill-guided; no agent-composed polling loops).

---

## Summary

Replace the current "agent runs `broker follow` in the background while it works" pattern with an explicit, foreground **read → execute → respond** loop driven by a new `/broker-mode` slash command. The agent waits for a message in the foreground, processes the resulting batch (asking the user when needed), sends a shape-matched reply, and loops.

The CLI changes to support this collapse `broker follow` into a one-shot batch receiver named `broker recv`, with two flags: `--timeout` (max wait for the first message) and `--burst-window` (post-first-arrival drain window). The streaming `broker follow` semantics are retired entirely.

The broker skill is rewritten so broker mode is the canonical pattern. The Monitor-tool streaming pattern and the freestanding "wait for a reply" canonical are removed.

## Motivation

The current broker skill recommends `broker follow --idle-timeout N` as the primitive for "wait for messages," with a separate Monitor-tool pattern for orchestrators that want per-message reactivity. This produces three problems:

1. **The agent ends up writing ad-hoc loops anyway.** Even when given `broker follow`, agents in real sessions reach for `while true; broker read; sleep N` shapes, dedup files in `/tmp`, and JSON parsing. The skill's anti-pattern doc exists because of this. Past feedback was explicit: skills should make the right pattern the easy pattern, not enforce it through prose.
2. **Background follow + Monitor encourages drift.** Once `broker follow` is running in the background, the agent has no structured place to "stop and process" — it's reactive to streamed lines, which is where ad-hoc parsing scripts emerge.
3. **The two-pattern menu is itself friction.** "Use broker follow for foreground waits, Monitor for background streaming, broker history for catch-up, broker read for one-shots" is too many primitives for the same job. Agents pick wrong, repeatedly.
4. **`broker follow` is also long-lived by design.** Today's `--idle-timeout` is genuinely *idle-after-activity*: the timer resets on every new message, so a follow can stream indefinitely under steady traffic. That long-lived shape is exactly what enables the orchestrator-watching-many-agents pattern (see `docs/patterns.md` "Orchestrator watching many agents," which uses `--idle-timeout 0` for indefinite streaming). Broker mode deliberately retires that shape.

Broker mode replaces the menu with one pattern: foreground, explicit, batch-oriented. The agent never decides when to stream-vs-wait; it just runs the loop.

## In scope

- New `/broker-mode` slash command.
- Rewritten broker skill (SKILL.md + relevant docs) with broker mode as the canonical pattern.
- New `broker recv` CLI subcommand with `--timeout` and `--burst-window` flags.
- Removal of `broker follow` and its `--idle-timeout` flag.
- Removal of the Monitor-tool streaming pattern from skill docs.

## Out of scope

- Server protocol changes (no changes to the Unix socket protocol, presence sockets, or message storage).
- Identity / authority / namespacing changes (existing rules apply unchanged inside the loop).
- Background-mode operation. There is no longer a documented background pattern.
- Migration shims for `broker follow`. The subcommand is removed cleanly; the skill is updated in lockstep.

## 1. The loop

The agent enters broker mode via `/broker-mode` and runs this loop until the user interrupts:

1. **Wait.** Run `broker recv` (no args). With default `--timeout 0`, this blocks indefinitely until a message arrives. On first arrival, `broker recv` keeps tailing the inbox log for `--burst-window` seconds (default 5) to capture follow-ups, then exits with the full batch on stdout.
2. **Process.** Read the drained batch as the input for this iteration. If multiple senders or threads are represented, treat them as separate sub-tasks within the same iteration. Apply existing authority rules (`docs/authority.md`): `user` and `@orchestrator/<scope>` DMs are commands, peer DMs are informational, conflicts get relayed upstream.
3. **Ask the user, if needed.** If the work requires information or approval the agent doesn't have, pause and ask the user directly (text or `AskUserQuestion`). The Claude turn ends; the user replies; the agent resumes mid-iteration. This is normal Claude Code behavior — broker mode does not change it.
4. **Reply.** Send a response per the **reply-shape rule**, applied **per inbound message** (not per batch — if the batch contained messages from multiple senders or threads, you produce multiple replies, one per inbound message):
   - Single-recipient DM → `broker send --to <sender>`.
   - Multi-recipient DM → `broker reply-all --to-message <MID>`.
   - Broadcast → `broker send --to <broadcaster>` (broadcasts have no stable recipient set, so reply-all errors).
   - If the agent recruited other agents during processing, ping them with separate explicit `broker send` calls — do not widen the reply.
5. **Loop.** Run `broker recv` again. Re-enter step 1.

The whole loop is consecutive Bash invocations within one Claude turn. There is no harness change, no scheduling, no background process.

### Exit conditions

- **User interruption.** Esc / Ctrl-C, "exit broker mode," or any redirecting instruction. The user is in the loop and owns its termination.
- **Broker server crash.** `broker recv` exits non-zero (socket error). The agent reports the failure and exits the loop. No silent retry — that would mask real outages. The user can re-invoke `/broker-mode` once the server is back.

There is no sentinel-message terminator and no idle-timeout terminator. The single off-switch is the user.

## 2. CLI changes

### `broker recv` (new)

Replaces `broker follow`. This is a behavioral replacement, not a flag rename — `broker recv` is a different primitive with different exit semantics.

```
broker recv [--timeout N] [--burst-window M] [--identity X]
```

Behavior:

- Wait up to `N` seconds for the first message. If `N=0` (the default), wait indefinitely. If the timer expires with no traffic, exit cleanly (code 0) with empty stdout.
- **Backlog-at-startup is treated as an arrival event.** If the inbox already has unread lines when `broker recv` starts, emit them immediately and begin the burst window — do *not* wait `--timeout` for additional traffic first.
- On the first arrival (whether it was already in the backlog or arrived during the wait), continue tailing the inbox log for `M` seconds (default 5). Any messages that arrive within that window are appended to the output. Then exit.
- `--burst-window 0` exits as soon as the first arrival has been delivered. If the first "arrival" was a multi-line backlog at startup, all of it is emitted as one atomic batch before exit — the `0` does not split a backlog.
- Stdout is the existing display-format lines, in arrival order. Cursor advances per emitted line, matching today's `broker follow`. Implication: if `broker recv` is killed (SIGINT, SIGKILL) mid-burst-window, every line that has been written to stdout has its cursor advance committed; lines not yet written remain in the backlog and are picked up by the next `broker recv`. There is no batch-level rollback.
- Exit code 0 on clean exit (timeout reached, or burst window completed). Non-zero on socket error or server-disconnect.

Notes on the semantic shift from `broker follow`:

- `broker follow --idle-timeout N` was *idle-after-activity*: the timer reset on every new message, so a follow could stream indefinitely under steady traffic. That long-lived shape is gone.
- `broker recv --burst-window M` is a *hard cap*: it does not extend on new arrivals. If a flood of messages keeps arriving past the cap, they pile up in the inbox backlog and are picked up by the next iteration's `broker recv`.
- These are different primitives, not the same primitive with renamed flags. Implementations should treat `broker recv` as new code, not a refactor of follow.

### Delivery mechanism

`broker recv` reads new lines from the inbox log file by polling at the same cadence used today (~0.2s), exactly as `broker follow` does. The Unix socket is used only for presence (see below) and identity registration — not for message delivery. This is unchanged from current behavior.

### Presence socket

`broker recv` opens the same presence socket that `broker follow` opens today, held for the full duration of the call. Implication for `broker clients` / `broker server`'s `who` view: an agent is shown as "live" only while it is *actively waiting in `broker recv`*. While the agent is processing a batch (running tools, sending replies, asking the user for input), it is *not* in `broker recv` and so appears "offline" in `broker clients`. This is the intended semantic: presence reflects readiness to receive, not liveness of the agent process.

The single-`broker recv`-per-identity rule from `broker follow` carries over unchanged. Two near-simultaneous `broker recv` invocations for the same identity will see the second rejected.

### `broker follow` (removed)

The subcommand and its `--idle-timeout` flag are deleted from the CLI. No deprecation period. Per the skill rewrite, no documented pattern still calls it.

### Other subcommands

Unchanged: `broker whoami`, `broker send`, `broker broadcast`, `broker reply-all`, `broker history`, `broker read`, `broker clients`, `broker server`.

## 3. Slash command

A new `/broker-mode` slash command ships with this plugin at `commands/broker-mode.md`. `.claude-plugin/plugin.json` is updated to add `"commands": "./commands/"` alongside the existing `"skills": "./skills/"` entry (the official superpowers plugin manifest demonstrates this layout — `commands` is a first-class top-level key).

The slash command does not invoke the broker skill via any auto-trigger mechanism. Instead, the slash command body explicitly tells the assistant to invoke the skill via the Skill tool — that is the linkage model. The body:

```
You are now operating in Broker Mode.

Invoke the broker skill (Skill tool) and follow its "Broker Mode" section.
Run the loop until the user instructs you to stop.
```

All procedural detail (the loop steps, reply-shape rules, exit conditions, authority guidance) lives in the skill. This keeps a single source of truth.

## 4. Skill changes

### SKILL.md

Add a new top-level **"Broker Mode"** section, structured as:

1. One-sentence summary: "Run an explicit foreground read-process-respond loop, one iteration per inbox batch."
2. The five-step loop, written as numbered imperatives.
3. The reply-shape rule (three lines).
4. One-line pointer to `docs/authority.md` for conflict handling.
5. Exit conditions.

Approximately 30–50 lines.

Update the existing **"Critical rules"** section: rule #1 ("Use `broker follow` to wait for messages") becomes "Use `/broker-mode` to wait for messages." The "don't `broker read` before `broker follow`" rule becomes the same, against `broker recv`.

Update the **frontmatter description** to mention broker mode as the canonical pattern, so an agent encountering the skill knows the loop is the default. The skill is invoked explicitly by the `/broker-mode` slash command body (see §3); no auto-trigger linkage is required.

Replace every `broker follow` reference in the Quick Reference table and the Canonical patterns examples with `broker recv`. Update the default-timeout language.

### `docs/patterns.md`

- Remove the standalone "Wait for a reply" canonical pattern. Inside broker mode, the agent never writes that pattern by hand.
- Remove the "Streaming into Claude Code's `Monitor` tool" section entirely.
- Rewrite the "Orchestrator watching many agents" section: orchestrators run broker mode like any other agent. They are agents that relay rather than implement, but the loop is identical.
- Keep the "Catch up after being away" section — `broker history` and `broker read` are still useful for one-shot situational awareness outside broker mode.
- Add a "Broker mode" section that mirrors and elaborates the SKILL.md summary, with a worked example of a full iteration.

### `docs/usage.md`

- Replace the `follow` reference section with a `recv` reference section.
- Update the `--idle-timeout` documentation to `--timeout`, and add `--burst-window`.

### `docs/troubleshooting.md`

- Keep the "while true; broker read; sleep" anti-pattern. Still applies inside broker mode (agents shouldn't replace `broker recv` with a homemade loop).
- Keep the "I ran `broker read` then `broker follow` and saw nothing" anti-pattern, but rewrite it for `broker recv`. The hazard (cursor advance hides backlog) is identical.
- The "`broker follow` exited with 'identity X already has an active follower'" entry is updated for `broker recv`. Identity-uniqueness still applies — only one `broker recv` per identity at a time.
- The "socket closed unexpectedly" entry is unchanged in spirit; just rename the command in the example. Add a one-line note that **broker mode does not retry on transient connection failure**: the next `broker recv` after a server crash exits non-zero, the agent reports the failure, and the user re-invokes `/broker-mode` after `broker server` is back. The contract that the inbox log + cursor persist across server restarts is unchanged — broker mode just doesn't paper over the brief outage.

### `docs/setup.md`

- Lines 38 and 71 (and any other live `broker follow` references) are rewritten for `broker recv`.
- The "broker server requirement" framing stays; only the example commands change.

### Files with no changes

- `docs/authority.md` — referenced by the broker mode loop (step 2) as authoritative for conflict handling. Content is unchanged.
- `docs/signals.md` — signal vocabulary (READY / BLOCKED / QUESTION / DECISION) is independent of the wait-for-message primitive. Unchanged.
- `docs/health-check.md` — diagnoses setup; not coupled to the wait primitive. Unchanged.

## 5. Edge cases

**Agent fails mid-task before sending a reply.** The triggering message has already been drained — the cursor is past it. The agent surfaces the failure to the user (it's in the active conversation) and decides how to proceed: retry, send a `BLOCKED:` DM to the original sender, or wait for user direction. Per the persistence requirement, every drained message remains on disk in the inbox log; post-hoc audit is fine.

**A message arrives during reply-send.** Standard broker behavior — it lands in the inbox. The next `broker recv` drains it as backlog and proceeds. No race.

**Multiple unrelated threads in one batch.** Treat as separate sub-tasks within one iteration: handle each, send a reply per thread (each scoped per the shape rule, per inbound message), then loop. The loop is "one iteration per batch," not "one iteration per task."

**`broker recv` returns empty.** Only possible if the user passed `--timeout > 0` explicitly. The skill default (`broker recv` no args, timeout=0) never produces this. The skill notes that empty output means "no messages, loop again," not "exit broker mode."

**Authority conflicts inside the loop.** Existing `docs/authority.md` rules apply unchanged. Broker mode introduces no new authority semantics — only a new cadence.

**`broker recv` killed mid-burst-window.** SIGINT or SIGKILL during the burst window is lossy at the per-line granularity: lines already written to stdout have had their cursor advance committed and won't be re-emitted; lines not yet written remain in the backlog. The agent does not re-process the killed iteration's partial batch — it loops, calls `broker recv` again, and picks up whatever is still in the backlog. Combined with on-disk persistence, this means no messages are *lost*; some may simply be received across two iterations instead of one.

**Broker server is mid-restart when `broker recv` is called.** `broker recv` exits non-zero (connection refused). Broker mode does not retry. The agent reports the failure and the loop ends. The user re-invokes `/broker-mode` once `broker server` is back. This is a deliberate trade: explicit failure reporting over hidden retries that could mask real outages.

**Agent appears "offline" while processing.** Because the presence socket is open only during `broker recv`, an agent in broker mode is shown as "live" only while waiting for the next batch. While processing (running tools, sending replies, asking the user), it appears "offline" in `broker clients` / `broker server`'s `who`. This is intended: presence reflects readiness to receive, not liveness of the agent process. Senders that need a stronger guarantee can use `broker send` regardless of presence — store-and-forward semantics still apply.

## 6. Versioning and migration

- **Version bump:** minor. The new skill section + breaking CLI change qualify per CLAUDE.md.
- **Release notes:** rename `docs/release-notes/upcoming.md` to `v{version}.md` and start a new `upcoming.md`. Same for `docs/changelogs/`.
- **Breaking changes:**
  - `broker follow` removed. Any external caller breaks. Per current state of the repo, no external callers exist.
  - `--idle-timeout` flag removed. Replaced by `--timeout` on `broker recv`.
- **Skill compatibility:** the broker skill is updated in the same commit as the CLI rename, so a user updating the plugin gets a coherent skill + CLI pair.

## 7. Testing

- Update existing `broker follow` tests to target `broker recv`, including:
  - Empty inbox with `--timeout 0`: blocks until first arrival, then drains burst window.
  - Empty inbox with `--timeout N`: exits empty after N seconds.
  - Backlog non-empty on entry: drains and waits burst window without consulting `--timeout`.
  - `--burst-window 0` with multi-line backlog: emits all backlog atomically, then exits.
  - `--burst-window 0` with single first arrival: emits one line, exits.
  - Burst-window hard cap: messages arriving within the window are emitted; messages arriving after the cap remain in the backlog and are picked up by a second `broker recv`.
  - Server crash mid-recv: exits non-zero.
  - Connection refused at recv start (server down): exits non-zero, no retry.
  - Identity uniqueness: second `broker recv` for same identity rejected (existing rule).
  - Presence socket lifetime: identity is "live" during recv, "offline" between recvs.
- Skill content is reviewed but not test-covered — no automated harness for skill prose in this repo.
- The slash command body is reviewed but not test-covered.

## 8. Alternatives considered

These alternatives surfaced during the brainstorming session and were rejected. Documenting them so the rationale doesn't have to be re-litigated.

- **Keep `broker follow` and add a `--exit-on-first-arrival` flag.** Single-command, less code change. Rejected because overloading `follow` with a second exit condition makes the contract harder to reason about. Two separate primitives (background-streaming follow vs. one-shot recv) are cleaner — and the streaming primitive isn't needed at all once broker mode is the default.
- **Keep streaming follow alongside broker mode.** Documented for orchestrator scenarios that genuinely want per-message reactivity. Rejected: the prior feedback memory was explicit that the two-pattern menu is itself friction. Orchestrators run broker mode like any other agent.
- **Sentinel-message-driven termination.** A specific message content (e.g. `EXIT` from `user`) breaks the loop, giving senders a remote off-switch. Rejected: adds an authority/security wrinkle (who can send a sentinel?) and a way for the loop to end unexpectedly. The user is present and can interrupt; that's enough.
- **Idle-timeout termination.** If no messages arrive for N minutes, exit broker mode automatically. Rejected for the same reason as the sentinel — silent termination is bad UX and the user can interrupt anyway.
- **`broker recv` retries once on connection refusal.** Smooths over server restarts. Rejected: explicit failure beats hidden retries; broker server restarts are rare and the user re-invoking `/broker-mode` is a fine recovery path.

## 9. Open questions

None at the time of writing. All design decisions resolved during brainstorming and review:
- Entry trigger: `/broker-mode` slash command + skill (skill carries procedure).
- Wait mechanism: `broker recv` with default `--timeout 0`, `--burst-window 5`.
- Termination: user-driven only.
- Reply behavior: shape-matched, applied per inbound message.
- Background follow patterns: removed entirely.
- Presence socket lifetime: tied to `broker recv` duration, not to the broker mode loop as a whole.
- Server-restart handling: no retry; explicit failure and exit.
