---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project's CLAUDE.md has a Documentation Sync section listing files and triggers. Use after completing any development work to update release notes and changelogs. Use when offering to cut a new version of a project.
---

# Documentation Sync

After completing code changes, check the project's `CLAUDE.md` for a `## Documentation Sync` section and evaluate each listed file's trigger before reporting the task complete. If the section is missing, ask the user if they'd like to add one — run `/skill-cefailures:documentation-sync:setup` to walk them through it.

## The Documentation Sync Section

Project owners add this section to their `CLAUDE.md`:

```markdown
## Documentation Sync

Before reporting any code change complete, invoke the `skill-cefailures:documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
- `CLI_GUIDE.md` [Public-CLI-API] — Updated when CLI behavior changes
- `docs/api.md` [Only-Breaking] — Only updated for breaking changes
```

The opening directive is a hint: it tells Claude to invoke the `skill-cefailures:documentation-sync` skill before reporting code-change work complete. It is not a hard guarantee — sessions that don't touch code can ignore it. But for any session that does change code, the directive is what surfaces the trigger-evaluation step instead of letting it slip.

Each entry has three parts:
1. **File path** — The document to potentially update
2. **Trigger** (in brackets) — When this file needs updating
3. **Description** — What the file is for and how to write updates for it

## Evaluating Triggers

### Trigger Reference

| Trigger | Fires When | Example |
|---------|-----------|---------|
| `Public-API` | Exported APIs, schemas, types, or public interfaces change — **excluding** any area covered by a more specific `Public-{Name}-API` entry in the same section | Renamed a function parameter, added a new export |
| `Public-{Name}-API` | Public interfaces change for a specific area of the codebase. `{Name}` is a descriptive label (not necessarily an exact folder path) that unambiguously identifies the area. | `Public-CLI-API` fires when CLI flags/behavior change; `Public-Auth-API` fires when auth endpoints change |
| `Any-Code-Change` | A **behavior-affecting** code change — anything that alters runtime behavior, build output, or visible API surface. **Does not fire** for cosmetic-only edits (formatting, whitespace, comments, lint autofixes, test-fixture rearrangement that doesn't change assertions). | Internal refactor, dependency bump that changes behavior, bugfix |
| `Only-Breaking` | Reverse-incompatible changes are introduced | Removed a parameter, changed return type, dropped support |

**Partition rule for `Public-API` and `Public-{Name}-API`:** When a Documentation Sync section lists both, the named entries carve their areas out of the generic `Public-API`. A CLI flag change fires `Public-CLI-API` only, not both. If no named entry covers the change, fall back to `Public-API`.

**Public-surface judgment call:** A symbol may be technically exported (e.g., re-exported by a barrel file) but have no documented public consumer — no mention in README, no entry in changelogs, no external callers visible. Renaming such a symbol is a fuzzy case: it triggers `Public-API` literally, but the user-facing impact is zero. **Ask the user** before treating these as Public-API rather than auto-updating public docs for a change nobody outside the codebase will notice.

### How to Evaluate

For each file listed in the Documentation Sync section:

1. **Read the trigger** in brackets
2. **Assess your code changes** against the trigger definition
3. **If the trigger fires**, update the file according to its description
4. **If the trigger does NOT fire**, skip the file

Be precise: an internal refactor does NOT fire `Public-API`. A new optional parameter does NOT fire `Only-Breaking`. Match the trigger definition exactly.

### Including Doc Updates in Implementation Plans

Whenever you write an implementation plan for a project that has a `## Documentation Sync` section, surface doc-update work in the plan — do not leave it as an implicit follow-up.

Pick one of two paths based on how concrete the planned scope is:

- **Concrete scope (feature, bugfix, well-defined refactor):** For each entry whose trigger you can confidently predict will fire, add a task that names the file (e.g., "Update `README.md` for the new `--verbose` flag").
- **Exploratory scope (investigation, "let's see what breaks," large refactors with unknown public-surface impact):** Add a single "Re-evaluate Documentation Sync triggers after implementation" task at the end of the plan rather than guessing per-file. Predicting per-file in this mode produces a misleading plan.

The point is to keep doc work visible — either as named-file tasks upfront, or as one explicit re-evaluation gate. Either is fine; an unmentioned doc update is what isn't.

## Companion docs and commands

These workflows are deeper than the core trigger-evaluation loop and live as sub-docs or commands so they only load when actually needed:

| Resource | Load when |
|----------|-----------|
| `docs/release-notes-and-changelogs.md` | The project uses the opt-in `docs/release-notes/` + `docs/changelogs/` structure AND you're writing entries, rotating `upcoming.md`, running the version cross-check, or migrating an existing `CHANGELOG.md`. Covers directory layout, release-notes vs. changelog distinction, hash-range entry format, recommended doc-sync entries, version cross-check, existing-project migration offers. |
| `docs/follow-ups.md` | The project uses the opt-in `docs/FOLLOWUPS.md` standing log AND you're prepending an entry, annotating an item as complete, or scanning for items that overlap the current task. Covers entry format, what counts vs. what doesn't, lifecycle, recommended doc-sync entry. |
| `/skill-cefailures:documentation-sync:setup` | The project's `CLAUDE.md` has no `## Documentation Sync` section and the user wants to add one. |
| `/skill-cefailures:documentation-sync:cut-version` | The user has agreed to a version cut (see "When to offer a version cut" below). Runs the bump-rotate-commit-tag recipe end-to-end. |

## When to offer a version cut

After a major set of changes has settled — a feature, a bug fix, a refactor, a docs sweep, or any combination the user clearly considers "done" — ask the user if they'd like to cut a new version. Don't offer mid-flow, and don't offer for trivial in-isolation edits. Don't bump the version yourself unless asked; phrase it as a question first ("Want me to cut v1.4.0 for this?"). When the user agrees, run `/skill-cefailures:documentation-sync:cut-version`.

## Common Mistakes

These are trigger-evaluation slips. Mistakes specific to release-notes/changelog work live in `docs/release-notes-and-changelogs.md`; version-cut mistakes live in the `:cut-version` command body.

| Mistake | Fix |
|---------|-----|
| Skipping doc updates under time pressure | Triggers are objective — evaluate them regardless of urgency |
| Treating `{Name}` in `Public-{Name}-API` as an exact path | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
