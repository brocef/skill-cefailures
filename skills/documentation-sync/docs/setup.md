# Setting Up Documentation Sync

If a project's CLAUDE.md has no `## Documentation Sync` section, ask the user: "Would you like to set up a Documentation Sync section in your CLAUDE.md?"

If they agree, help them fill it out by asking:
1. **Which files** should be kept in sync with code changes? (e.g., README.md, CHANGELOG.md, guides)
2. **What trigger** applies to each file? Offer the pre-defined triggers from the SKILL.md "Trigger Reference" table.
3. **What description** should guide how updates are written for each file?

Then add the section to their CLAUDE.md in the format shown in the SKILL.md "The Documentation Sync Section" example. **Always include the opening directive line** that tells Claude to invoke the `skill-cefailures:documentation-sync` skill — without it, future sessions may see the file list but skip the trigger-evaluation logic.

### Create Tracked Files (and Folders) That Don't Yet Exist

After adding the section, create any tracked files — **and their parent directories** — that don't already exist so the agent has somewhere to write on the first trigger fire. Use the conventional initial content for each:

- **`docs/release-notes/` and `docs/changelogs/` directories**, each containing an `upcoming.md` file — create the directories if they don't exist; both `upcoming.md` files start with just a `# Upcoming` heading. Apply this only when the project's section lists the per-version structure (some projects use only GitHub Releases or a single root `CHANGELOG.md` — don't impose this layout if it isn't listed).
- **`docs/FOLLOWUPS.md`** (when the user adopts the Follow-ups pattern from SKILL.md `## Follow-ups`) — create the `docs/` directory if it doesn't exist; initial content is the standard header plus a one-line description of the prepend-and-annotate convention so future readers don't have to reverse-engineer it:

  ```markdown
  # Follow-ups

  Standing log of deferred code-related follow-up items. New entries are prepended; completed items are annotated in place (strikethrough + completion date), not deleted.
  ```

- **Other listed files** (e.g., guides, CLI docs) — only create stubs if the user explicitly asks; otherwise leave them for the user to author.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not creating the changelog file if it doesn't exist | If the file is listed in Documentation Sync, create it if missing |
| Omitting the opening directive line | The skill must be reloaded each session; the directive is what triggers that |
