---
description: Send a broker DM to one or more identities, a broadcast, or a reply-all against a prior message.
---

Read `skills/broker/docs/usage.md` in this plugin for the full reference: `broker send --to a,b`, `broker broadcast`, `broker reply-all --to-message MID`. Use the form that matches the user's intent.

Before composing the message body, also read `skills/broker/docs/signals.md` so the body starts with the appropriate signal (READY / BLOCKED / QUESTION / DECISION) when applicable, and `skills/broker/docs/critical-rules.md` to avoid the broadcast-reply-shape pitfall.

If `$ARGUMENTS` is provided, treat it as the user's message intent — but still confirm the recipient list and signal choice before actually sending.
