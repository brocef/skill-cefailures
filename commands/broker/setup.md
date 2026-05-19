---
description: Guide the user through first-time broker setup — symlink the CLI, start the server, confirm identity, register the Bash(broker:*) permission.
---

Read `skills/broker/docs/setup.md` in this plugin and walk the user through first-time broker setup. The doc covers install (symlinking `broker_cli.py` onto `$PATH`), running the server, identity derivation (and how to pin it with `broker init`), reserved identities (`user`, `human`, `BROADCAST`, `@orchestrator/<scope>`), and the on-disk storage layout.

Ground every step in the user's actual environment: check what's already in place before suggesting an action, and skip steps the user has already completed. After setup, recommend `/skill-cefailures:broker:doctor` to verify everything is wired up correctly.
