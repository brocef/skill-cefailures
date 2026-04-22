# Broker Signal Vocabulary

Short, structured prefixes agents put at the start of DMs and broadcasts to make inter-agent state machine-readable at a glance. A project's `CLAUDE.md` can override or extend these. The vocabulary is orthogonal to transport — it applies equally to `broker send`, `broker broadcast`, and `broker reply-all`.

## The four signals

### `READY: <what>`

An unblocking milestone has landed. Use when you've completed work other agents may be waiting on.

```bash
broker broadcast "READY: @proposit/proposit-core v1.2.3 published to npm"
broker send --to proposit-server "READY: /api/auth endpoint shipped behind X-Test-Mode"
```

### `BLOCKED: <on-whom> <what>`

You are stuck waiting on someone. Name them explicitly.

```bash
broker send --to proposit-core "BLOCKED: TypeError from validate() on empty schemas"
broker send --to human "BLOCKED: which endpoint shape do you want — flat or nested?"
```

### `QUESTION: <target> <what>`

Open question that needs input. If the target is a specific agent, address them in `--to` and mention them in the content so reply-all threads read cleanly.

```bash
broker send --to proposit-core "QUESTION: @proposit-core should validate() take a schema or a raw object?"
broker send --to human "QUESTION: @human are we freezing main for the mobile cut tomorrow?"
```

### `DECISION: <topic> → <choice>`

A coordination question has been resolved. Especially useful for closing a `reply-all` thread so the outcome is captured in every participant's inbox.

```bash
broker reply-all --to-message "$MID" "DECISION: validate() signature → validate(schema, object)"
broker broadcast "DECISION: mobile release cut → 2026-03-05 at 18:00 UTC"
```

## When to use each

- Post `READY` as soon as a milestone lands — don't wait for someone to ask. Broadcast if everyone cares; DM the specific waiter if only one agent is blocked on you.
- Post `BLOCKED` immediately when you realize you can't make progress. Name the blocker in the content AND address them via `--to`.
- Use `QUESTION` when you need input but can work on something else in the meantime.
- Use `DECISION` to snapshot the outcome of a discussion — ideally via `reply-all` on the question DM so everyone who was in the thread sees it.

## Why these signals matter

Orchestrators and humans scan their inbox for signal prefixes to decide what to route, unblock, or escalate. A message like "I guess we could maybe do X or Y" is invisible; "QUESTION: @orchestrator should we do X or Y?" in the orchestrator's inbox is actionable.

## Matching patterns

If you're scanning your own inbox (e.g. in `broker history`), grep for the prefix:

```bash
broker history | grep -E '\] (READY|BLOCKED|QUESTION|DECISION):'
```

The line format is stable and agent-facing — plain `grep` is fine; no jq required.
