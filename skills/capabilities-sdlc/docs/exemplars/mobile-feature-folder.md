# auth — capabilities (cross-screen)

> **Exemplar.** This file lives in the `capabilities-sdlc` skill, not in any production repo. It demonstrates the format for a mobile **feature folder**'s `capabilities.md` — capabilities that span multiple screens. A real file would live at `proposit-mobile/src/auth/capabilities.md`. Screen-local capabilities (which buttons exist on `LoginScreen`, what happens on tap) live in the screen file (`src/screens/LoginScreen/capabilities.md`); this file describes the cross-screen *flow* and *guarantees*.

## Authenticate via OAuth
**Status:** Supported

A user starting from `LoginScreen` taps either Google or Apple sign-in. The app opens `expo-auth-session`'s system browser to the provider's consent screen. On success the system browser closes and the app receives the resulting Google or Apple ID token; the app POSTs that token to `proposit-server`'s `/api/auth/google` (or `/api/auth/apple`) and stores the returned session cookie via `expo-secure-store`. The user lands on the Home tab. The user does not navigate manually — the screen transition is automatic upon a successful POST.

## Persist session across app launches
**Status:** Supported

When the app launches, the auth feature reads the secure store. If a session is present and not expired, the user lands on Home without seeing `LoginScreen`. If absent or expired, `LoginScreen` is shown. Session expiry is checked client-side against the JWT's `exp` claim; the app does not call the server to verify.

## Sign out
**Status:** Supported

From the settings menu (`SettingsScreen`), the user taps "Sign out." The app clears the secure store, navigates back to `LoginScreen`, and discards any in-memory user state. The server-side session cookie is not separately revoked — server sessions are short-lived enough that local clearing suffices.

## Re-authenticate silently on session expiry
**Status:** Missing

When the session JWT expires mid-use, the user currently sees a "Session expired, please sign in" message and is bounced to `LoginScreen`. The desired capability: silently re-run the OAuth handshake using cached refresh tokens, surfacing the user-facing flow only if silent refresh fails. Blocked on the server-side refresh-token capability (`/api/auth/google#post-refresh-an-existing-session`, currently `Missing`).
