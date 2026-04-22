---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, sending DMs between agents, or when the user asks you to talk to another agent. Use when you see references to the broker command, inboxes, or agent identities.
---

# Broker

A DM/inbox CLI for multi-agent Claude Code. Every agent has a persistent identity derived from its workspace and a per-identity inbox on disk. Messages persist regardless of whether the recipient is online. Use `broker follow` to drain your inbox and stream new messages as they arrive — no polling, no conversation IDs to track.

## Prerequisites

- The broker server must be running (`broker server` in a terminal).
- `Bash(broker:*)` must be in your `allowedTools`.

## Your identity

The broker derives your identity from your cwd:

1. Nearest `package.json` walking up from cwd → its `name` field (e.g. `@proposit/shared`, `proposit-server`).
2. Otherwise, `git remote get-url origin` → `<org>/<repo>` (e.g. `Proposit-App/proposit-mobile`).
3. Otherwise, error.

Run `broker whoami` to confirm. The CLI auto-fills `--identity` from cwd when omitted, so you usually don't pass it. **To address another agent, compute their identity from their project — there is no directory to browse.**

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker whoami` | Print the identity the CLI will use from this cwd |
| `broker send --to a,b CONTENT` | DM one or more recipients |
| `broker broadcast CONTENT` | Fan out to every registered identity |
| `broker reply-all --to-message MID CONTENT` | Reply to all recipients of a prior DM, excluding self |
| `broker follow [--idle-timeout N]` | Block, drain inbox, stream new DMs as they arrive |
| `broker history [--from X] [--since ISO] [--sent]` | Read inbox (or outbox) without advancing the cursor |
| `broker read` | Advance cursor; print only new inbox lines since last read |

## Critical rules

1. **Use `broker follow` to wait for messages.** Do not write `while true; broker read; sleep N`. Follow drains + streams + exits on idle/timeout.
2. **Don't `broker read` before `broker follow`.** Read advances the cursor past the backlog; if you then follow, the backlog is already gone. Use `follow` alone.
3. **Don't parse broker output with `jq` / `python`.** The line format is already agent-facing — read it directly.
4. **To reply to a broadcast, use `send --to <broadcaster>`, not `reply-all`.** Broadcasts have no stable recipient set, so reply-all has no room to address.

## Canonical patterns

Wait for a reply:
```bash
broker send --to proposit-server "READY: shared v1.2.3 published"
broker follow --idle-timeout 120
```

Announce to everyone:
```bash
broker broadcast "BLOCKED: npm registry is down, pausing publishes"
```

Multi-party thread with reply-all:
```bash
MID=$(broker send --to a,b,c "QUESTION: should validate() take a schema?")
broker follow --idle-timeout 120
broker reply-all --to-message "$MID" "DECISION: schema wins"
```

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference, storage layout, display format |
| `docs/patterns.md` | Canonical patterns: wait-for-reply, broadcast, reply-all, catch-up, monitor streaming |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) |
| `docs/troubleshooting.md` | Anti-patterns and fixes — read if you catch yourself writing a loop |
| `docs/setup.md` | Install, server, reserved identities, storage layout |
