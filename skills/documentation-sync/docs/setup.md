# Setting Up Documentation Sync

If a project's CLAUDE.md has no `## Documentation Sync` section, ask the user: "Would you like to set up a Documentation Sync section in your CLAUDE.md?"

If they agree, help them fill it out by asking:
1. **Which files** should be kept in sync with code changes? (e.g., README.md, CHANGELOG.md, guides)
2. **What trigger** applies to each file? Offer the pre-defined triggers from the Trigger Reference (see `docs/evaluating-triggers.md`).
3. **What description** should guide how updates are written for each file?

Then add the section to their CLAUDE.md in the format shown in the SKILL.md "The Documentation Sync Section" example.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not creating the changelog file if it doesn't exist | If the file is listed in Documentation Sync, create it if missing |
