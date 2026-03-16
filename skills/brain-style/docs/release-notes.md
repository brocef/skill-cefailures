# Release Notes & Changelog Style

## Directory Structure

```
docs/
  release-notes/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized release notes for v1.2.3
  changelogs/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized changelog for v1.2.3
```

File names follow the pattern `v{version}.md`. The `upcoming.md` files hold content for the next version, whose number is not yet known (could be a micro, minor, or major bump).

## Release Notes vs. Changelogs

| Aspect | Release Notes (`docs/release-notes/`) | Changelog (`docs/changelogs/`) |
|--------|----------------------------------------|--------------------------------|
| Audience | End-users | Developers (contributors, dependents) |
| Tone | Plain language, understandable by anyone familiar with the app | Technical, precise |
| Content | User-facing changes only | All changes including internals, refactors, dependency bumps |
| Detail level | What changed and why it matters to the user | What changed, where, and how |

### Release Notes Guidance

- Write in plain language — no jargon, no internal module names
- Focus on outcomes: what can the user now do, what was fixed, what changed
- Group by category when useful (e.g., "New Features", "Bug Fixes", "Breaking Changes")
- Omit purely internal changes (refactors, dev tooling, test-only changes)

### Changelog Guidance

- Include everything: features, fixes, refactors, dependency changes, CI/CD updates, test additions
- Reference file paths, function names, or modules where helpful
- Group by category (e.g., "Added", "Changed", "Fixed", "Removed", "Internal")
- Be specific enough that a developer can understand the scope without reading the diff

## Post-Work Behavior

After completing any development work, **offer to update the release notes and changelog**. This is the default — you are asking the user whether they want to *skip* the update, not whether they want to *do* it. Frame it as:

> "I'll update the release notes and changelog to reflect these changes. Want me to skip that?"

If the user does not object, update both `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` with the changes just completed.

## Version Cross-Check

Before writing to `upcoming.md`, cross-check the project's current version (from `package.json`, `pyproject.toml`, `Cargo.toml`, `version.txt`, or whatever the project uses) against existing versioned files in `docs/release-notes/` and `docs/changelogs/`.

If the project version has been bumped and a corresponding `v{version}.md` file does **not** exist yet, the content currently in `upcoming.md` likely belongs to that version. In that case:

1. Rename (or copy) `upcoming.md` to `v{version}.md` in both directories
2. Start a fresh `upcoming.md` for subsequent work

If `v{version}.md` already exists but `upcoming.md` has content that predates the bump, merge the `upcoming.md` content into the versioned file and clear `upcoming.md`.

Always check this before appending — never silently lose content that should be attributed to a released version.
