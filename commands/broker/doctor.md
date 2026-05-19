---
description: Diagnose the broker setup — a 5-point health check covering $PATH, the CLI symlink, server reachability, the Bash(broker:*) permission, and version drift.
---

Read `skills/broker/docs/health-check.md` in this plugin and walk through the diagnostic procedure exactly as written.

Three fixes — symlink, permission, version match — can be applied with the user's confirmation. The remaining two — adding `~/.local/bin` to `$PATH`, starting the server — are user actions; surface them as instructions, don't try to perform them.

Report findings as a checklist (✓ / ✗) so the user can see at a glance what's healthy and what isn't.
