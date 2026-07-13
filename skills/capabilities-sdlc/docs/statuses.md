# Capability statuses

Three values, exhaustively. Capability files describe *intended* state — bugs and regressions are tracked elsewhere.

## Supported

The capability works today.

This is the default for any documented capability that is implemented. The body describes what the user can do, the trigger (the action that initiates the capability), and the outcome (what changes for the user).

Body content rule: focus on the user's mental model, not the implementation. If the capability is "Sign in with Google", the body says "the user taps the button, sees Google's consent screen, lands on Home" — not "the OAuth ID token is validated against `iss`, `aud`, and `exp` claims." Implementation belongs in code comments and architecture docs.

## Missing

The capability is desired but not implemented.

The body explains *why* the capability is desired and *what unblocks it*. If there's a planned initiative that will deliver the capability, name it. If there's a specific blocker (a missing endpoint, a third-party dependency, a design decision), name it.

`Missing` is the backlog signal. Humans and agents grep for `**Status:** Missing` to see what we want but haven't built. A `Missing` entry should be specific enough that someone reading it could write the implementation plan.

## Omitted

The capability is deliberately not supported.

The body explains *why the omission* and *where the alternative lives* (if there is one). For example: "Password sign-in is omitted because this application delegates authentication to an external identity provider. Users recover access through that provider."

`Omitted` exists for clarity. It's not a backlog item; it's a documented decision so future readers don't waste time wondering if the capability is missing-but-coming or missing-on-purpose.

## What about broken capabilities?

A fourth status ("Known broken" / "Blocked") was considered and rejected. Capability files describe intended state. If a `Supported` capability is broken in production, that's a bug — track it in `FOLLOWUPS.md`, GitHub issues, or whatever bug-tracking system the repo uses. Do not change the status to "broken" in the capability file; the documented intent ("this is what the user can do") remains the same even if the current implementation has a regression.

## Choosing a status when you're not sure

- Does the user-facing capability work right now, in the current production state? → `Supported`.
- Do we want it but haven't built it? → `Missing`.
- Have we explicitly decided not to build it? → `Omitted`.
- Is it broken in production but supposed to work? → Still `Supported` in the capability file; file a bug report somewhere else.
- Is it documented as `Supported` but turns out to never have worked? → See the *discovery fix* note in `docs/planning-gate.md`.
