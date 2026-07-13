# Sign in — capabilities

> **Exemplar.** This demonstrates a user-facing web route in a co-located layout. A comparable file could live at `apps/web/src/app/sign-in/capabilities.md`.

## Sign in with an identity provider
**Status:** Supported

A returning user selects “Sign in” and is redirected to the configured identity provider. After successful authorization, the browser returns to `/api/session`, establishes a session, and redirects to `/dashboard`. Cancellation returns the user to `/sign-in` with a clear message.

## Continue to account registration
**Status:** Supported

A visitor without an account can follow the registration link. The registration route explains the required consent before starting the same external authorization flow.

## Sign in with a local password
**Status:** Omitted

This application delegates authentication to an external identity provider and does not collect passwords. Account recovery is handled by that provider.

## Sign in with an emailed link
**Status:** Missing

The product intends to support emailed sign-in links for users who cannot complete the external provider flow. Delivery and token-consumption endpoints are not implemented yet.
