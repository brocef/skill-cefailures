---
name: broker
description: Explicit invocation only. Use only when the user explicitly names the broker skill, runs `/broker-mode`, asks to enter Broker Mode, asks to use broker, or asks you to send/read broker DMs. Do not auto-load merely because a task mentions collaboration, other agents, inboxes, identities, or the broker command.
---

# Broker

A DM/inbox CLI for multi-agent Claude Code. Every agent has a persistent identity derived from its workspace and a per-identity inbox on disk. This skill is opt-in: invoke it only when the user explicitly asks for broker usage or enters `/broker-mode`.

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
