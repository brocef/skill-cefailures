---
description: Read the broker inbox — `broker recv` (advances the cursor) by default, or `broker history` (read-only) for peeking.
---

Read the `broker recv` and `broker history` sections of `skills/broker/docs/usage.md` in this plugin to understand the cursor-advancing vs. read-only distinction and the message display format.

Default behavior: `broker recv --burst-window 5` to drain new inbox lines and advance the cursor. If the user says "peek", "look at history", or otherwise signals they don't want the cursor to move, use `broker history` (with `--since` or `--from` if they specify a window).

Display each message using the format described in `usage.md` — do not invent your own.
