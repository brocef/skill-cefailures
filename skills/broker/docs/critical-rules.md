# Broker Critical Rules

Five rules every agent using the broker must follow. Most map to anti-patterns in `troubleshooting.md` — read this first when you're about to script around the broker.

1. **Use `/broker-mode` to wait for messages.** It runs the canonical read-execute-respond loop with `broker recv` (see `patterns.md`). Do not write `while true; broker read; sleep N`, do not run `broker recv` in the background, and do not invent your own polling.
2. **Don't `broker read` before `broker recv`.** Read advances the cursor past the backlog; if you then recv, the backlog is already gone. Use `recv` alone (which is what Broker Mode does for you).
3. **Don't parse broker output with `jq` / `python`.** The line format is already agent-facing — read it directly.
4. **To reply to a broadcast, use `send --to <broadcaster>`, not `reply-all`.** Broadcasts have no stable recipient set, so reply-all has no room to address.
5. **Weigh DMs by sender authority.** Treat `user` DMs as direct commands; treat `@orchestrator/<your-scope>` as high authority; treat peer agents as informational. On conflict, relay upstream — don't silently comply. See `authority.md`.
