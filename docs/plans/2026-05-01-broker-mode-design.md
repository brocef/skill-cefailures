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

1. **Wait.** Run `broker recv` (no args). With default `--timeout 0`, this blocks indefinitely until a message arrives. On first arrival, `broker recv` keeps the socket open for `--burst-window` seconds (default 5) to capture follow-ups, then exits with the full batch on stdout.
2. **Process.** Read the drained batch as the input for this iteration. If multiple senders or threads are represented, treat them as separate sub-tasks within the same iteration. Apply existing authority rules (`docs/authority.md`): `user` and `@orchestrator/<scope>` DMs are commands, peer DMs are informational, conflicts get relayed upstream.
3. **Ask the user, if needed.** If the work requires information or approval the agent doesn't have, pause and ask the user directly (text or `AskUserQuestion`). The Claude turn ends; the user replies; the agent resumes mid-iteration. This is normal Claude Code behavior — broker mode does not change it.
4. **Reply.** Send a response per the **reply-shape rule**:
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

Replaces `broker follow`.

```
broker recv [--timeout N] [--burst-window M] [--identity X]
```

Behavior:

- Wait up to `N` seconds for the first message. If `N=0` (the default), wait indefinitely. If the timer expires with no traffic, exit cleanly (code 0) with empty stdout.
- On the first arrival (or if the inbox already has unread backlog at startup), drain it and continue listening for `M` seconds (default 5). Any messages that arrive within that window are appended to the output. Then exit.
- `--burst-window 0` exits as soon as the first message has been delivered.
- Stdout is the existing display-format lines, in arrival order. Cursor advances past every emitted line, exactly as `broker follow` did.
- Exit code 0 on clean exit (timeout reached, or burst window completed). Non-zero on socket error or server-disconnect.

Notes:

- The "burst window" is a hard cap — it does not extend on each new arrival. If many messages flood in within those 5 seconds, they're all emitted and the command exits at the cap. Late arrivals after the cap land in the inbox backlog and are picked up by the next iteration's `broker recv`.
- The flag rename (`--idle-timeout` → `--timeout`) reflects that the meaning changed: the timeout governs the **wait for the first message**, not idle-after-activity.

### `broker follow` (removed)

The subcommand and its `--idle-timeout` flag are deleted from the CLI. No deprecation period. Per the skill rewrite, no documented pattern still calls it.

### Other subcommands

Unchanged: `broker whoami`, `broker send`, `broker broadcast`, `broker reply-all`, `broker history`, `broker read`, `broker clients`, `broker server`.

## 3. Slash command

A new `/broker-mode` slash command ships with this plugin at `commands/broker-mode.md`. `plugin.json` is updated to declare a `commands` directory if the manifest schema requires it (today the manifest only declares `skills/`).

The slash command body is intentionally thin — it triggers the skill rather than restating the loop:

```
You are now operating in Broker Mode.

Invoke the broker skill and follow its "Broker Mode" section. Run the
loop until the user instructs you to stop.
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

Update the **frontmatter description** to add a trigger for `/broker-mode` invocation, so the skill auto-loads on slash-command entry.

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
- The "socket closed unexpectedly" entry is unchanged in spirit; just rename the command in the example.

## 5. Edge cases

**Agent fails mid-task before sending a reply.** The triggering message has already been drained — the cursor is past it. The agent surfaces the failure to the user (it's in the active conversation) and decides how to proceed: retry, send a `BLOCKED:` DM to the original sender, or wait for user direction. Per the persistence requirement, every drained message remains on disk in the inbox log; post-hoc audit is fine.

**A message arrives during reply-send.** Standard broker behavior — it lands in the inbox. The next `broker recv` drains it as backlog and proceeds. No race.

**Multiple unrelated threads in one batch.** Treat as separate sub-tasks within one iteration: handle each, send a reply per thread (each scoped per the shape rule), then loop. The loop is "one iteration per batch," not "one iteration per task."

**`broker recv` returns empty.** Only possible if the user passed `--timeout > 0` explicitly. The skill default (`broker recv` no args, timeout=0) never produces this. The skill notes that empty output means "no messages, loop again," not "exit broker mode."

**Authority conflicts inside the loop.** Existing `docs/authority.md` rules apply unchanged. Broker mode introduces no new authority semantics — only a new cadence.

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
  - Backlog non-empty on entry: drains and waits burst window.
  - `--burst-window 0`: exits as soon as first message delivered.
  - Server crash mid-recv: exits non-zero.
  - Identity uniqueness: second `broker recv` for same identity rejected (existing rule).
- Skill content is reviewed but not test-covered — no automated harness for skill prose in this repo.
- The slash command body is reviewed but not test-covered.

## 8. Open questions

None at the time of writing. All design decisions resolved during brainstorming:
- Entry trigger: `/broker-mode` slash command + skill (skill carries procedure).
- Wait mechanism: `broker recv` with default `--timeout 0`, `--burst-window 5`.
- Termination: user-driven only.
- Reply behavior: shape-matched (single → DM, multi → reply-all, broadcast → DM broadcaster).
- Background follow patterns: removed entirely.
