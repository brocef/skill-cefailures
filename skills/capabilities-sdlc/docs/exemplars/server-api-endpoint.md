# /api/session — capabilities

> **Exemplar.** This demonstrates a multi-method API endpoint in a co-located layout. A comparable file could live at `apps/api/src/routes/session/capabilities.md`.

## POST: Exchange an authorization token for a session
**Status:** Supported

An API client submits a signed authorization token. The endpoint validates its signature, issuer, audience, and expiry, then returns the current user's profile and sets a secure session cookie. Invalid or unknown tokens return `401` without creating a session.

## POST: Create an account implicitly
**Status:** Omitted

The endpoint does not create accounts for unknown identities. New users complete the registration flow first so account creation and required consent remain explicit.

## POST: Refresh an existing session
**Status:** Missing

Clients should be able to extend an eligible session without repeating interactive authorization. The refresh-token storage design and rotation policy remain undecided.

## DELETE: Revoke the current session
**Status:** Supported

An authenticated client can revoke its current session. The endpoint clears the session cookie and invalidates the server-side session record before returning `204`.
