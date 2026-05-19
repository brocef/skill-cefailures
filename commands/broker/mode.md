---
description: Enter Broker Mode — the foreground read-execute-respond loop, one iteration per inbox batch.
---

You are now operating in Broker Mode.

Read the **Broker Mode** section of `skills/broker/docs/patterns.md` in this plugin, then run the loop it describes. Before responding to any DM, also read these mandatory shared docs in the same `skills/broker/docs/` directory:

- `critical-rules.md` — the five rules every broker agent must follow (no polling loops, no jq, broadcast reply shape, etc.).
- `authority.md` — sender authority hierarchy (`user` > `@orchestrator/<your-scope>` > peer agents).
- `signals.md` — signal vocabulary (READY / BLOCKED / QUESTION / DECISION).

Consult `troubleshooting.md` if you catch yourself drifting into an anti-pattern.

Run the loop until the in-conversation user instructs you to stop, or until a DM from the reserved `user` identity instructs you to exit.
