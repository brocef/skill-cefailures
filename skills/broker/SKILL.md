---
name: broker
description: Reserved namespace for the broker DM/inbox CLI's shared reference docs (`docs/critical-rules.md`, `docs/signals.md`, `docs/authority.md`, etc.). All broker workflows are slash commands — `/skill-cefailures:broker:setup`, `:mode`, `:send`, `:read`, `:doctor`. Do not auto-load this skill on mentions of broker, inbox, DM, identity, or collaboration.
---

# broker

Shared reference docs for the broker DM/inbox CLI live under `docs/`. Commands under `commands/broker/` read these by path; this SKILL.md does not route. If you reached this file via auto-trigger, exit and let the user invoke the relevant slash command instead.
