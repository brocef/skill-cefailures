# Capabilities file format

## Granularity

One `## <Capability>` heading per discrete user action. Use natural-language imperative ("Sign in with Google", not "googleSignIn" or "Login Screen"). One heading per *thing the user does*.

## Skeleton

```markdown
# <Subject> — capabilities

## <Capability name>
**Status:** Supported

<1–3 short paragraphs describing what the user can do, the trigger, and the outcome.>

## <Another capability name>
**Status:** Missing

<Why we want it; what unblocks it; or what initiative is planned.>

## <Yet another>
**Status:** Omitted

<Why this is deliberately not supported; where the alternative lives.>
```

## Conventions

- **Top-level heading.** `# <Subject> — capabilities`. The subject names what the file is about: route name, screen name, feature folder name, API endpoint path.
- **Capability heading.** A `##` heading per capability, in natural-language imperative form. For API routes, use the form `## <METHOD>: <action>` (e.g., `## POST: Validate Google ID token and start session`). A single method may have multiple headings — e.g., one `## POST: ...` describing what the endpoint does (Supported) and another `## POST: ...` describing what it deliberately does not do (Omitted).
- **Status line.** Immediately after the heading (no blank line between), `**Status:** Supported | Missing | Omitted` on a single line, then a blank line, then the body content.
- **Body length.** 1–3 short paragraphs. Long enough to be useful for orientation; short enough that nobody resents updating it. If a capability needs more than three paragraphs, it's probably two capabilities.

## Reference style

Same-repo only. A `capabilities.md` may reference another `capabilities.md` *within the same repo* using `<path>#<heading-slug>`; cross-repo references are not permitted (see `docs/product-layer-coordination.md` for how cross-repo coordination happens instead). The heading slug is the same one GitHub-flavored markdown renders: lowercase, words joined by hyphens, punctuation stripped.

Example: `src/screens/LoginScreen/capabilities.md#sign-in-with-google` references the "Sign in with Google" capability in the LoginScreen file.

For headings with parenthetical or punctuation-heavy names, the slug strips punctuation: `Reset password (email)` becomes `reset-password-email`. When in doubt, render the file in any markdown viewer and copy the heading anchor.

## What is *not* part of the format

- **No frontmatter.** Capability files have no YAML frontmatter. The file's location (path) and headings are sufficient identifiers.
- **No formal IDs.** Each capability is identified by its heading anchor, not a separately-maintained slug.
- **No cross-repo links.** A `capabilities.md` in `proposit-server` does not link to or reference a path in `proposit-mobile` (or vice versa).
- **No "broken" or "blocked" status.** Capability files describe *intended* state. Bugs and regressions are tracked separately (e.g., `FOLLOWUPS.md`, GitHub issues).

## Body content rules per status

See `docs/statuses.md` for the per-status content expectations.
