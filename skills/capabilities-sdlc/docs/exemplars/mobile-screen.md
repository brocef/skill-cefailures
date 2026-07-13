# LoginScreen — capabilities

> **Exemplar.** This demonstrates screen-local behavior in a co-located mobile layout. A comparable file could live at `apps/mobile/src/screens/LoginScreen/capabilities.md`; cross-screen session behavior belongs in the authentication feature file.

## Sign in with an identity provider
**Status:** Supported

The screen displays a “Sign in” button. Selecting it opens the system browser for external authorization. On success, the authentication feature handles the transition away from this screen.

## Continue to registration
**Status:** Supported

A “Create an account” link opens `RegistrationScreen`, which explains consent requirements before authorization begins.

## Sign in with email and password
**Status:** Omitted

The screen has no password fields because the application delegates authentication to an external identity provider.

## Recover a local password
**Status:** Omitted

There is no local password to recover. Users regain access through the configured identity provider.
