---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project's CLAUDE.md has a Documentation Sync section listing files and triggers.
---

# Documentation Sync

After completing code changes, check the project's `CLAUDE.md` for a `## Documentation Sync` section. If present, evaluate each listed file's trigger to decide what documentation to update before considering the task done.

## When to Use

- After making ANY code change, before reporting task completion
- When a project's CLAUDE.md contains a `## Documentation Sync` section

When NOT to use:
- Changes are limited to documentation files only (no code was changed)

If the `## Documentation Sync` section is **missing** from CLAUDE.md, ask the user if they'd like to add one. If yes, help them fill it out (see "Setting Up Documentation Sync" below). If no, fall back to general judgment.

## The Documentation Sync Section

Project owners add this section to their `CLAUDE.md`:

```markdown
## Documentation Sync

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `changelogs/next.md` [Any-Code-Change] — Gist of changes with commit hash range
- `CLI_GUIDE.md` [Public-CLI-API] — Updated when CLI behavior changes
- `docs/api.md` [Only-Breaking] — Only updated for breaking changes
```

Each entry has three parts:
1. **File path** — The document to potentially update
2. **Trigger** (in brackets) — When this file needs updating
3. **Description** — What the file is for and how to write updates for it

## Trigger Reference

| Trigger | Fires When | Example |
|---------|-----------|---------|
| `Public-API` | Exported APIs, schemas, types, or public interfaces change | Renamed a function parameter, added a new export |
| `Public-{Name}-API` | Public interfaces change for a specific area of the codebase. `{Name}` is a descriptive label (not necessarily an exact folder path) that unambiguously identifies the area. | `Public-CLI-API` fires when CLI flags/behavior change; `Public-Auth-API` fires when auth endpoints change |
| `Any-Code-Change` | Any code change occurs, regardless of scope | Internal refactor, dependency bump, bugfix |
| `Only-Breaking` | Reverse-incompatible changes are introduced | Removed a parameter, changed return type, dropped support |

### Evaluating Triggers

For each file listed in the Documentation Sync section:

1. **Read the trigger** in brackets
2. **Assess your code changes** against the trigger definition
3. **If the trigger fires**, update the file according to its description
4. **If the trigger does NOT fire**, skip the file

Be precise: an internal refactor does NOT fire `Public-API`. A new optional parameter does NOT fire `Only-Breaking`. Match the trigger definition exactly.

## Changelog Commit Hash Ranges

When updating a changelog file (or any file whose description mentions commit hashes), wrap entries with the first and last commit hashes that introduced the changes:

```markdown
## Changes

<changes starting-hash="abc1234" ending-hash="def5678">
- Renamed `host` parameter to `hostname` in `createClient`
- Added optional `timeout` parameter to `createClient`
</changes>
```

Where `abc1234` is the first commit hash and `def5678` is the last commit hash of the changes being documented.

**To get commit hashes**, run:
```bash
# Most recent commit
git rev-parse --short HEAD

# If multiple commits were made, get the range
git log --oneline -n <number_of_commits>
```

**Skip commit hash wrappers if:**
- `git` is not installed or not available
- The current working directory is not a git repository
- The user has explicitly asked not to include commit references

In these cases, write the changelog entries without the `<changes>` wrappers.

## Setting Up Documentation Sync

If a project's CLAUDE.md has no `## Documentation Sync` section, ask the user: "Would you like to set up a Documentation Sync section in your CLAUDE.md?"

If they agree, help them fill it out by asking:
1. **Which files** should be kept in sync with code changes? (e.g., README.md, CHANGELOG.md, guides)
2. **What trigger** applies to each file? Offer the pre-defined triggers from the Trigger Reference table.
3. **What description** should guide how updates are written for each file?

Then add the section to their CLAUDE.md in the format shown in "The Documentation Sync Section" above.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping doc updates under time pressure | Triggers are objective — evaluate them regardless of urgency |
| Updating `[Public-API]` files for internal refactors | Internal changes don't fire `Public-API`. Check the trigger. |
| Forgetting commit hashes in changelog | Run `git rev-parse --short HEAD` after committing |
| Treating `{Name}` in `Public-{Name}-API` as an exact path | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
| Not creating the changelog file if it doesn't exist | If the file is listed in Documentation Sync, create it if missing |
