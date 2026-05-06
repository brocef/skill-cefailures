---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, sending DMs between agents, or when the user asks you to talk to another agent. Use when you see references to the broker command, inboxes, or agent identities. Broker Mode (`/broker-mode`) is the canonical pattern for agents waiting on inbound work — explicit foreground read-execute-respond loop, one iteration per inbox batch.
---

# Broker

A DM/inbox CLI for multi-agent Claude Code. Every agent has a persistent identity derived from its workspace and a per-identity inbox on disk. Use `/broker-mode` to wait on inbound work — no polling, no conversation IDs to track.

| Doc | Scope |
|-----|-------|
| `docs/setup.md` | Install, server, identity resolution, reserved identities, storage layout |
| `docs/usage.md` | CLI quick reference + full per-command reference, message display format |
| `docs/patterns.md` | Broker Mode loop, broadcasts, reply-all, catch-up, one-shot building blocks |
| `docs/critical-rules.md` | The five rules every agent must follow (no polling loops, no jq, broadcast reply shape, etc.) |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) |
| `docs/authority.md` | Sender authority hierarchy; read on first contact and on conflicting directives |
| `docs/troubleshooting.md` | Anti-patterns and fixes — read if you catch yourself writing a loop |
| `docs/health-check.md` | Diagnose setup ("is broker working", "broker doctor", "diagnose broker") |
