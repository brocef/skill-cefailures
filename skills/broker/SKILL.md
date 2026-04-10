---
name: broker
description: Use when collaborating with other agents, coordinating with other Claude Code instances, joining multi-agent conversations, or when the user asks you to talk to another agent. Use when you see references to the broker command or conversation IDs.
---

# Broker

A chatroom-like CLI for multi-agent conversations. Multiple Claude Code agents and a human can talk to each other in real time through a shared broker server.

## Prerequisites

- The broker server must be running (`broker server` in a terminal)
- `Bash(broker:*)` must be in your allowedTools

## Quick Reference

| Command | Description |
|---------|-------------|
| `broker list --identity NAME` | List conversations |
| `broker create --identity NAME TOPIC [--content "seed"]` | Start a conversation |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message |
| `broker read --identity NAME CONV_ID` | Read new messages |
| `broker join --identity NAME CONV_ID` | Join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker members --identity NAME CONV_ID` | List who's in a conversation |
| `broker close --identity NAME CONV_ID` | Close a conversation (read-only) |

All commands output JSON to stdout. Errors output JSON to stderr with exit code 1.

## Polling Pattern

Unless the user says otherwise, keep polling for new messages:

1. Call `broker read --identity <your-name> <conversation_id>`
2. Process any messages and respond with `broker send`
3. Repeat until the conversation is closed or you receive a stop message

Do NOT stop polling unless explicitly told to.

## Docs

| Doc | When to read |
|-----|-------------|
| `docs/usage.md` | Full CLI reference with examples and JSON output formats |
| `docs/setup.md` | Installation, configuration, and first-time setup |
