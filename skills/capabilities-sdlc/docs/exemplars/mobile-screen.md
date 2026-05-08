# LoginScreen — capabilities

> **Exemplar.** This file lives in the `capabilities-sdlc` skill, not in any production repo. It demonstrates the format for a mobile **screen-component** `capabilities.md` — capabilities specific to this screen. A real file would live at `proposit-mobile/src/screens/LoginScreen/capabilities.md`. Cross-screen flow context (the full OAuth handshake, session persistence) lives in the feature-folder file (`src/auth/capabilities.md`); this file describes what the user does *on this screen*.

## Sign in with Google
**Status:** Supported

The screen displays a "Sign in with Google" button using the standard Google brand colors. Tapping it opens the system browser via `expo-auth-session`. The user does not return to this screen on success — the auth feature handles the redirect (see `src/auth/capabilities.md#authenticate-via-oauth`).

## Sign in with Apple
**Status:** Supported

The screen displays a "Sign in with Apple" button below the Google button. Tapping it opens Apple's native sign-in sheet on iOS, or the OAuth web flow on Android. iOS flow is the polished default; Android flow is functional but visually less integrated.

## Switch to signup flow
**Status:** Supported

Below the OAuth buttons, a "Don't have an account? Sign up" text link navigates to `SignupScreen`. The signup screen offers the same OAuth flow but pre-checks the terms-of-service consent box.

## Sign in with email and password
**Status:** Omitted

This screen does not show email/password fields. Proposit does not support password authentication (see `src/auth/capabilities.md` for the full feature-level rationale).

## Recover a forgotten password
**Status:** Omitted

There is no "Forgot password?" link on this screen because passwords are not used. Users who can't access their Google or Apple account must recover access through that provider, not through Proposit.
