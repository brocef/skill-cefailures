# /api/auth/google — capabilities

> **Exemplar.** This file lives in the `capabilities-sdlc` skill, not in any production repo. It demonstrates the format for a server API endpoint's `capabilities.md`, including the multi-method case. A real file would live at `proposit-server/src/app/api/auth/google/capabilities.md`. The TypeBox request and response schemas live in `@proposit/shared` — this file captures contract *semantics* on top of those schemas.

## POST: Validate Google ID token and start session
**Status:** Supported

An API client (web frontend or `proposit-mobile`) submits a Google ID token in the request body. The endpoint validates the token's signature against Google's public keys, checks the `aud` matches the configured Proposit OAuth client ID, and matches the token's `sub` to an existing Proposit user. On match, it issues a session JWT in an `httpOnly` cookie and returns the user's profile. On signature failure, expired token, or unknown subject, it returns `401`.

## POST: Auto-create Proposit account from Google profile
**Status:** Omitted

The endpoint does not auto-create a Proposit account when the Google `sub` is unknown. Users must complete `/signup` (which itself uses OAuth) before they can sign in. This decision exists to keep account creation explicit so first-time users see the terms-of-service consent screen.

## POST: Refresh an existing session
**Status:** Missing

A separate flow that lets a client extend its session without re-prompting the user. Required for the planned long-running mobile session initiative. Blocked on the session-refresh-token storage scheme being designed.

## GET: Inspect session
**Status:** Omitted

Session inspection happens via `/api/auth/session` (a different endpoint), not via this one. `/api/auth/google` is exclusively the Google-OAuth completion endpoint.
