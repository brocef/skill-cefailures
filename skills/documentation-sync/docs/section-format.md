# The Documentation Sync Section

Project owners add this section to their `CLAUDE.md`:

```markdown
## Documentation Sync

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
- `CLI_GUIDE.md` [Public-CLI-API] — Updated when CLI behavior changes
- `docs/api.md` [Only-Breaking] — Only updated for breaking changes
```

Each entry has three parts:
1. **File path** — The document to potentially update
2. **Trigger** (in brackets) — When this file needs updating
3. **Description** — What the file is for and how to write updates for it
