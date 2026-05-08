# Login — capabilities

> **Exemplar.** This file lives in the `capabilities-sdlc` skill, not in any production repo. It demonstrates the format for a server user route's `capabilities.md`. A real file would live at `proposit-server/src/app/(nofooter)/login/capabilities.md`.

## Sign in with Google
**Status:** Supported

A returning user lands on the login page and taps the "Sign in with Google" button. The browser navigates to Google's OAuth consent screen; on success, Google redirects back to `/api/auth/google` (see that endpoint's capabilities) which establishes a Proposit session and redirects to `/home`. Failure or cancellation returns the user to `/login` with an error toast describing what went wrong.

## Sign in with Apple
**Status:** Supported

Identical to "Sign in with Google" but routed through Apple's OAuth. The user taps "Sign in with Apple"; Apple's sign-in sheet appears; on success the page completes the same `/home` redirect. Apple OAuth surfaces no profile picture by default, so the post-sign-in `/home` greeting falls back to initials.

## Sign in with email and password
**Status:** Omitted

Proposit does not store passwords. Authentication is OAuth-only (Google + Apple). New users who try to sign in with an unrecognized email are routed to the dedicated `/signup` flow, which itself uses OAuth.

## Magic-link sign-in
**Status:** Missing

Required for the planned passwordless onboarding initiative — a way for users to authenticate without leaving Mail/Messages. Blocked on transactional email setup (the magic-link delivery channel) and on a `/api/auth/magic-link/{token}` endpoint that does not yet exist.
