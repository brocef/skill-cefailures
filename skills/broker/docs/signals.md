# Broker Signal Vocabulary

Short, structured prefixes agents use in the main coordination room to make inter-agent state machine-readable at a glance. A project's `CLAUDE.md` can override or extend these.

## The four signals

### `READY: <what>`

An unblocking milestone has landed. Use when you've completed work other agents may be waiting on.

```
[core] READY: @proposit/proposit-core v1.2.3 published to npm
[server] READY: /api/auth endpoint shipped behind the X-Test-Mode header
```

### `BLOCKED: <on-whom> <what>`

You are stuck waiting on someone. Name them explicitly.

```
[server] BLOCKED: core TypeError from validate() on empty schemas
[server] BLOCKED: human which endpoint shape do you want — flat or nested?
```

### `QUESTION: <target> <what>`

Open question that needs input. If the target is a specific agent, `@mention` them.

```
[server] QUESTION: @core should validate() take a schema or a raw object?
[orchestrator] QUESTION: @human are we freezing main for the mobile cut tomorrow?
```

### `DECISION: <topic> → <choice>`

A coordination question has been resolved. Useful when the discussion happened in a side conversation and you want the main room to carry the outcome.

```
[server] DECISION: validate() signature → validate(schema, object)
[orchestrator] DECISION: mobile release cut → 2026-03-05 at 18:00 UTC
```

## When to use each

- Post `READY` as soon as a milestone lands — don't wait for someone to ask.
- Post `BLOCKED` immediately when you realize you can't make progress. Name the blocker.
- Use `QUESTION` when you need input but can work on something else in the meantime.
- Use `DECISION` to snapshot the outcome of a discussion, especially one that happened in a side room.

## Why these signals matter

The orchestrator and humans scan the main room for signals to decide what to route, unblock, or escalate. A message like "I guess we could maybe do X or Y" is invisible; a message like "QUESTION: @orchestrator should we do X or Y?" is actionable.
