# Authentication — capabilities

> **Exemplar.** This demonstrates a cross-screen mobile feature in a co-located layout. A comparable file could live at `apps/mobile/src/features/auth/capabilities.md`; screen-local actions belong in their screen capability files.

## Authenticate through an external provider
**Status:** Supported

A user starts sign-in from `LoginScreen`, completes authorization in the system browser, and returns to the application. The client exchanges the result with the session API, stores the session in platform-secure storage, and automatically opens the home screen.

## Persist a session across application launches
**Status:** Supported

At launch, the feature reads secure storage. A valid session opens the home screen; an absent or expired session opens `LoginScreen`.

## Sign out
**Status:** Supported

From settings, the user selects “Sign out.” The application revokes the server session, clears secure storage and in-memory user state, and returns to `LoginScreen`.

## Refresh a session without interrupting the user
**Status:** Missing

When a session expires during use, the application currently asks the user to sign in again. Silent refresh depends on the session API's planned refresh capability.
