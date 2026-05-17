# Product-layer coordination protocol

## Why this protocol exists

Proposit has a two-layer capability model:

- **Per-repo** capability files (`capabilities.md`) co-located with code in `proposit-server` and `proposit-mobile`.
- **Shared product-layer** files in `proposit-orchestration/docs/capabilities/<area>.md` describing what *the product* lets users do, platform-agnostic.

A per-repo agent in `proposit-server` does not read `proposit-orchestration/docs/capabilities/`. The cross-repo coupling rule is strict: per-repo files do not link or reference anything outside their own repo. The product layer is the orchestrator's artifact alone.

Without coordination, two per-repo agents authoring the "same" capability on web and mobile could drift — same intent, different language, divergent over time. This protocol prevents drift by routing product-layer questions through the orchestrator.

This protocol describes the *contract* between per-repo agents and the orchestrator. It is agnostic to the inter-agent transport — the host project's `CLAUDE.md` names the transport in use; this skill names only the request/response shape and the fallback rules.

## When a per-repo agent should query the orchestrator

When the agent is authoring a capability and at least one of these is true:

- The capability is plausibly cross-platform (it exists or could exist on both web and mobile).
- The capability has product-level wording the orchestrator might already know.
- The capability is about to be marked `Missing` and the agent suspects this is product-wide intent, not just a repo-local gap.

A typical query:

> "Authoring `src/screens/LoginScreen/capabilities.md`. Has 'Sign in with Google' been documented at the product level? If yes, please share the canonical wording so I align."

The orchestrator answers from `proposit-orchestration/docs/capabilities/`. If the capability is new at the product level, the orchestrator drafts the product-layer entry now or defers to reconciliation later (per the orchestrator's session-boundary reconciliation cadence).

## What the orchestrator sends back

The minimum useful answer:

- The product-layer wording for that capability (a paragraph, not the whole product-layer file).
- The product-layer status (`Supported`, `Missing`, `Omitted`).
- Any platform-specific divergence flagged in product-layer commentary.

The orchestrator does **not** send the per-repo agent the product-layer file's `**Realized in:**` list — those paths name sibling repos and would force the per-repo agent to acknowledge them. The agent gets the wording, not the cross-repo bookkeeping.

## Coordination-unavailable fallback

If the orchestrator is unreachable (the agent is running outside a coordinated session, or the orchestrator agent is not running):

1. **Author the capability based on in-repo evidence alone.** Walk the code, infer the user-facing behavior, and write the capability description from that evidence.
2. **Mark the body with a leading uncertainty line** as the *first* paragraph of the body, in italics:

   ```markdown
   ## Sign in with Google
   **Status:** Supported

   _TODO: confirm wording with orchestrator product layer._

   <rest of the body as authored>
   ```

3. **Surface the uncertainty in the human review summary** when reporting work complete. List each capability that carries the TODO marker and the reason (orchestrator unavailable).

The orchestrator reconciles wording at its next session-boundary reconciliation, removing the TODO marker once product-layer wording is confirmed.

## What this protocol is *not*

- **Not a remote read.** The agent does not gain access to `proposit-orchestration/docs/capabilities/` files. It receives only what the orchestrator chooses to relay.
- **Not a synchronous block.** The agent does not pause indefinitely waiting for an answer. If the coordination round-trip exceeds a reasonable wait (judgment call), proceed with the unavailable-fallback.
- **Not a substitute for review.** Even capabilities that get clean orchestrator answers are subject to human review.
