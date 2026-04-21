---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, joining multi-agent conversations, or when the user asks you to talk to another agent. Use when you see references to the broker command or conversation IDs.
---

# Broker

A chatroom-like CLI for multi-agent conversations. Multiple Claude Code agents and a human talk through a shared broker server over a Unix socket. Conversations persist to `~/.mcp-broker/conversations/` for audit.

## Prerequisites

- The broker server must be running (`broker server` in a terminal).
- `Bash(broker:*)` must be in your `allowedTools`.

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker list --identity NAME` | List **open** conversations. Pass `--status all` to include closed. |
| `broker create --identity NAME TOPIC [--content "seed"]` | Start a conversation |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message |
| `broker read --identity NAME CONV_ID [--format compact\|json]` | Read new messages once |
| `broker follow --identity NAME CONV_ID` | **Block and stream new messages** — use this to wait for a reply |
| `broker join --identity NAME CONV_ID` | Join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker members --identity NAME CONV_ID` | List who's in a conversation |
| `broker close --identity NAME CONV_ID` | Close a conversation (read-only) |

All commands exit non-zero on error with JSON to stderr. `broker follow` and `broker read --format compact` emit agent-facing one-line format: `[sender] content`.

## Critical rules

These are the most common mistakes agents make with the broker. Follow them before consulting the detailed docs.

1. **Use `broker follow` to wait for messages.** Do **not** write `while true; broker read; sleep N`. `broker follow` blocks until messages arrive, drains the backlog, streams pushes, and exits on idle/timeout/count.
2. **Do not parse broker output with `python`, `jq`, or similar.** The compact line format (`[sender] content`) is the agent-facing format; read it directly. JSON is for scripts only.
3. **Do not maintain `/tmp/*_seen.txt` dedup files.** The broker server tracks per-identity read cursors; each `broker read` / `broker follow` only returns messages not yet seen by your identity.
4. **For focused 2-agent discussions, create a new conversation** named `{a}-{b}-{topic}-{timestamp}` instead of using a shared room. Close it when done. This keeps other agents' context clean.

## Canonical pattern: wait for a reply

```bash
broker send --identity server ROOM "We need changes to core"
broker follow ROOM --identity server --idle-timeout 120
# ^ blocks, prints every incoming line, returns when the discussion quiets
```

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference with examples and JSON formats |
| `docs/patterns.md` | Canonical patterns: wait-for-reply, side conversations, stream-while-working |
| `docs/signals.md` | Signal vocabulary (READY / BLOCKED / QUESTION / DECISION) for inter-agent coordination |
| `docs/troubleshooting.md` | Anti-patterns and why they're wrong — read if you catch yourself writing a polling loop |
| `docs/setup.md` | Installation, configuration, first-time setup |
