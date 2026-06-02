 I want to expand the scope, flexibility, and structure of the `capabilities-sdlc` skill and related commands. I'm not talking necessarily about the skill itself in this repo, but rather the SDLC procedure that it describes.

  My target objectives for projects that use this skill:
  - Living documentation of all current, planned, or deliberately omitted capabilities of the project
  - Structure of actual docs folders and files leverages hierarchy so that we can avoid having excessively large files
    - Avoiding large files is critical to prevent context bloat
  - Folder names, hierarchy and file names are "self-documenting" in that their purpose is obvious before even reading the files
  - Cross-references between documentation files encouraged and supported by the skill to eliminate redundancy
  - Integration with third-party services like Confluence/Jira, GitHub Issues, etc. is likely in the future so we should design this with that in mind
    - Things like "this capability is tracked by this Jira ticket" and having a manual (or automatic) process to sync that status between them
  - Expand the different status values we have and formalize what they represent
    - We should have statuses like "partially-supported" and "blocked". Would like to hear proposals for other statuses which would be helpful.
  - Support for priorities
  - Formalize document structure
    - What section(s) should documents have? Different sections based on different document type?
  - Elaborating more on how inter-document references look and work, I'm going to sketch out a contrived example on what it could look like to demonstrate some more capabilities that I'd like the SDLC to have.

Let's assume the project is some sort of NextJS web application with a frontend, backend, and database.

The app might have the following structure:
- src/app/login/page.tsx
  - Login page route
- src/app/profile/page.tsx
  - Profile page route
- src/app/api/auth/login/route.ts
  - `/api/auth/login` API route handlers
- src/frontend/components/client/complex-styled-button.tsx
  - Some sort of reuseable styled button with a complex implementation (many possible states, perhaps), in `client/` as it has a `"use client"` directive and cannot be rendered on the server with SSR
- src/frontend/components/server/footer.tsx
  - The footer component, in `server/` as it can safely be rendered on the server with SSR
- src/model/index.ts
  - Some sort of database model implementation

I could imagine that the capabilities would be documented like this:
- docs/capabilities/routes/login
  - /capabilities.md
    - The login page's capabilities (`src/app/login/page.tsx`), not the API route
- docs/capabilities/routes/api/auth/login.md
  - The capabilities for the `/api/auth/login` route
- docs/capabilities/routes/profile
  - /
- docs/capabilities/components/footer.md
  - Very simple set of capabilities, does not even need to be a folder
- docs/capabilities/components/complex-styled-button
  - Note: Let's assume that the capabilities are different enough between the button when an icon is present and without it that there are state-specific capabilities documents as denoted by their names
  - /capabilities.md
    - Common capabilities that all <ComplexStyledButton> share
  - /with-icon.md
    - Capabilities that only apply to the button when an icon is present (ie. <ComplexStyledButton icon={iconComponent}>)
  - /without-icon.md
    - Capabilities that only apply to the button when no icon is present

In the `docs/capabilities/routes/login/capabilities.md` file, we might say that there should be a login button that uses the complex styled button with the login icon. I would like to say this in a very identifiable way in that we can infer that all the capabilities of that component are now available within this context. Perhaps it could look like:

```md
# Login Page Capabilities

## User can log in with a login form
User is able to enter a username and password into input fields and either press enter or click the login button to submit their credentials.

The login button should use the `/assets/login.png` icon with the `components/complex-styled-button` component.
```

By specifying `components/complex-styled-button`, we can safely infer that it's referring to `docs/capabilities/components/complex-styled-button` as the `docs/capabilities` is shared among all of these files and the rest of the path directs to the component.

Things that my example does not cover, but I would like to consider supporting:
- Versions/commits/branches in the component identifier (e.g. `components/complex-styled-button@origin/main` or `components/complex-styled-button@origin/feat/some-branch` if we need to specify that the spec for that button changed in a branch and that's what we should be using here)
- States as part of the formal syntax
  - e.g. `components/complex-styled-button[icon]` to indicate that we want the capabilities of that button with an icon vs `components/complex-styled-button[!icon]` which indicates the no-icon state vs `components/complex-styled-button` which implies that both states apply or are irrelevant
    - Could even go further and say `components/complex-styled-button` for only common capabilities and `components/complex-styled-button[*]` for all states
- Metadata for components/pages
  - Could use special folders+files per component to declare metadata
    - Assume we have `docs/capabilities/routes/api/auth/`
      - `docs/capabilities/routes/api/auth/errors.[md|yaml|json]`
        - Documents all possible error scenarios
          - "Password incorrect", "Email not found", "MFA Failure", etc.
        - Could be JSON/YAML instead of .md so that it's computer-readable if that's something we want
    - `docs/capabilities/components/complex-styled-button/states.[md|yaml|json]`
      - Document states of the button if that's important, e.g. "pressed", "hover", "disabled", etc.
  - Permission(s) required to use it
- App-level information
  - Define conditions which might be relevant across all apps
    - "When logged in" condition could be defined as `authed`
      - e.g. `If authed: capability X should be present`
  - Authorization information
    - "Users can have a variety of roles and the app behavior changes depending on what role they are assigned. See docs/capabilities/roles.md for details."

**Overall summary of this:** I want to have documents which describe in *natural language* how the application works. The purpose is three-fold:
1. It is much easier to understand how something is supposed to work if you read the natural language description of the behavior as opposed to having to read code which may or may not be well documented
2. Change requests, typically, are written by the human engineer and those requests are easier to make in natural language
3. Having a natural language description of how the application *should* behave is a good baseline to work off of and to audit existing code. Having a source of truth allows AI agents to verify that the implementation and tests match the desired reality.

As a last note, I'd also like to have you do some research on tools that currently exist which do something similar. No point in re-creating the wheel.