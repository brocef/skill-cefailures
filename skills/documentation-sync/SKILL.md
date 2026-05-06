---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project's CLAUDE.md has a Documentation Sync section listing files and triggers. Use after completing any development work to update release notes and changelogs. Use when offering to cut a new version of a project.
---

# Documentation Sync

After completing code changes, check the project's `CLAUDE.md` for a `## Documentation Sync` section and evaluate each listed file's trigger before reporting the task complete. If the section is missing, ask the user if they'd like to add one (see `docs/setup.md`).

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

## Release Notes & Changelogs

**This structure is opt-in.** The `docs/release-notes/` and `docs/changelogs/` layout described below applies only when the project's `## Documentation Sync` section explicitly lists `upcoming.md` files (or when the user asks you to set the structure up — see `docs/setup.md`). Don't create `docs/release-notes/upcoming.md` or `docs/changelogs/upcoming.md` in a project that hasn't adopted them. Some projects use only GitHub Releases, only a root `CHANGELOG.md`, or have no version-history files at all — that's a valid choice.

For monorepos, each package may carry its own `docs/release-notes/` and `docs/changelogs/` directories, or the repo may share a single set at the root. Follow whatever the project's `## Documentation Sync` section points to; don't infer a structure that isn't listed.

### Directory Structure

```
docs/
  release-notes/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized release notes for v1.2.3
  changelogs/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized changelog for v1.2.3
```

File names follow the pattern `v{version}.md`. The `upcoming.md` files hold content for the next version, whose number is not yet known (could be a patch, minor, or major bump).

### Release Notes vs. Changelogs

| Aspect | Release Notes (`docs/release-notes/`) | Changelog (`docs/changelogs/`) |
|--------|----------------------------------------|--------------------------------|
| Audience | End-users | Developers (contributors, dependents) |
| Tone | Plain language, understandable by anyone familiar with the app | Technical, precise |
| Content | User-facing changes only | All changes including internals, refactors, dependency bumps |
| Detail level | What changed and why it matters to the user | What changed, where, and how |

**Release notes guidance:**
- Write in plain language — no jargon, no internal module names
- Focus on outcomes: what can the user now do, what was fixed, what changed
- Group by category when useful (e.g., "New Features", "Bug Fixes", "Breaking Changes")
- Omit purely internal changes (refactors, dev tooling, test-only changes)

**Changelog guidance:**
- Include everything: features, fixes, refactors, dependency changes, CI/CD updates, test additions
- Reference file paths, function names, or modules where helpful
- Group by category (e.g., "Added", "Changed", "Fixed", "Removed", "Internal")
- Be specific enough that a developer can understand the scope without reading the diff

### Changelog Entry Format

Wrap changelog entries with commit hash ranges so readers can trace changes back to source:

```markdown
<changes starting-hash="abc1234" ending-hash="def5678">
- Renamed `host` parameter to `hostname` in `createClient`
- Added optional `timeout` parameter to `createClient`
</changes>
```

Where `abc1234` is the first commit and `def5678` is the last commit of the changes being documented.

```bash
# Get the most recent commit hash
git rev-parse --short HEAD

# Get a range if multiple commits were made
git log --oneline -n <number_of_commits>
```

**Skip hash wrappers** if git is unavailable, the directory is not a repo, or the user has asked not to include them. In those cases, write entries without the `<changes>` wrappers.

### Recommended Documentation Sync Entries

Projects using this structure should include these entries in their CLAUDE.md `## Documentation Sync` section:

```markdown
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes; plain language, no jargon
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
```

The trigger system determines when these files get updated — release notes fire on public-facing changes, changelogs fire on any code change.

### Version Cross-Check

Before writing to `upcoming.md`, cross-check the project's current version (from `package.json`, `pyproject.toml`, `Cargo.toml`, `version.txt`, or whatever the project uses) against existing versioned files in `docs/release-notes/` and `docs/changelogs/`.

Two scenarios surface drift:

- **Version bumped, no `v{version}.md` exists yet:** the content currently in `upcoming.md` likely belongs to that version. **Tell the user what you found and confirm before renaming.** Do not silently rotate files.
- **`v{version}.md` exists but `upcoming.md` has older content that predates the bump:** the `upcoming.md` content needs to be merged into the versioned file. Again, confirm with the user before merging — losing or relocating an entry without acknowledgment is worse than asking.

After confirmation, the rotation is:
1. Rename `upcoming.md` to `v{version}.md` in both directories
2. Start a fresh `upcoming.md` for subsequent work

Always run the cross-check before appending — never silently lose content that should be attributed to a released version, and never silently rename files the user didn't ask you to rename.

### Existing Project Migration

**Migration is always offered, never executed unilaterally.** Do not rewrite, move, or delete a project's existing CHANGELOG, release notes, or version-history files without explicit user approval. The table below lists *suggestions you can offer* — not a script to run.

When first working in a project, check whether it already has release notes or changelogs in a different format or location (e.g., a single `CHANGELOG.md` at the root, a `CHANGES.txt`, release notes embedded in `README.md`, GitHub Releases only, or a `docs/` subfolder with a different naming scheme).

If something similar exists but does not match the structure described above, describe what you found, explain how it differs, and ask whether the user wants to migrate. Frame it as a recommendation:

> "This project has a `CHANGELOG.md` at the root. Want me to migrate it to the per-version structure under `docs/changelogs/` and `docs/release-notes/`?"

Only after the user agrees, follow the suggestion below. Always preserve the original content during migration — either by incorporating it into the new structure, or by keeping the original file with a note that it has been superseded. Never silently overwrite or delete.

**Suggested migrations to offer:**

| What you find | Migration to propose |
|---------------|----------------------|
| Single root `CHANGELOG.md` | Split into `docs/changelogs/` per-version files; extract user-facing entries into `docs/release-notes/` |
| Release notes in `README.md` | Extract into `docs/release-notes/` per-version files; remove or replace the README section with a pointer |
| Flat `docs/changelog.md` or similar | Restructure into per-version files under `docs/changelogs/` and `docs/release-notes/` |
| Per-version files with different naming (e.g., `1.2.3.md` without `v` prefix) | Rename to `v{version}.md` |
| Only GitHub Releases (no files in repo) | Pull release content into `docs/release-notes/` and `docs/changelogs/` per-version files |
| Correct structure but missing one side (e.g., changelogs exist but no release notes) | Generate the missing side from the existing content |

## Follow-ups

`docs/FOLLOWUPS.md` is a standing log of deferred work items from completed feature implementations. Unlike release notes and changelogs — which are time-windowed records of what shipped — this file *grows* when work is deferred and *shrinks* when that work is later completed.

**This file is opt-in.** Use it only when the project's `## Documentation Sync` section lists it. Don't create `docs/FOLLOWUPS.md` in a project that hasn't adopted it.

### Entry Format

Each entry follows this template:

```markdown
# Work Summary Title
Commit range: abc1234-def5678
Branch name: feat/some-new-feature
Added on: 2026-05-06

## Follow-up Items
- Item 1
- Item 2

## Additional Notes
- Anything else relevant but not an action item
```

- **Title** — Brief description of the work that produced these follow-ups.
- **Commit range** — Starting and ending short hashes for the relevant work, so readers can trace it back.
- **Branch name** — The feature branch the work was done on. **Use the original branch name even if it has been merged and deleted from the remote** — other machines and stale clones may still carry it.
- **Added on** — Calendar date the entry was added; `YYYY-MM-DD` recommended for sortability.

New entries go at the top of the file (most recent first).

### What Counts as a Follow-up

**Include** code-related deferred work:
- Post-migration cleanups (e.g., "remove deprecated `/v1/users` endpoint after confirming all clients moved to `/v2`")
- Hardening skipped for scope (e.g., "add authorization controls to the new analytics routes")
- Refactors that emerged mid-task but weren't in scope
- Test coverage gaps the implementation revealed
- Performance work pushed out

**Exclude** anything that depends on a person doing something out-of-band:
- Smoke tests by the user
- Manual QA passes
- Stakeholder reviews or approvals
- "Verify in staging"

Those belong elsewhere — a tracker, a Slack ping, the PR description. If the item already shipped, it goes in the changelog or release notes. FOLLOWUPS.md is only for code work that hasn't happened yet.

### Lifecycle

- **At the end of feature work**, ask: was anything deferred? If yes, prepend a new entry block. If nothing was deferred, leave the file alone — don't write empty entries.
- **When picking up new work**, scan FOLLOWUPS.md for items overlapping the task at hand. Sometimes the lowest-effort path is finishing something already half-planned.
- **When a follow-up item is completed**, do not delete the bullet — annotate it so the historical record is preserved and future readers don't mistake completed work for outstanding work. Strike through the item text and append a completion date:

  ```markdown
  ## Follow-up Items
  - ~~Remove deprecated `/v1/users` endpoint after migration~~ (completed 2026-05-10)
  - Add authorization controls to the new analytics routes
  ```

  Edit or annotate `## Additional Notes` similarly when a note becomes obsolete rather than deleting it outright.
- **Do not rotate this file on version cuts.** Unlike `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`, FOLLOWUPS.md is a standing log that spans versions — items are annotated as they complete, not rotated when a version is tagged.

### Recommended Documentation Sync Entries

Projects using this convention should include this entry in their CLAUDE.md `## Documentation Sync` section:

```markdown
- `docs/FOLLOWUPS.md` [Any-Code-Change] — Standing log of deferred follow-up items; prepend an entry (commit range, branch, date) when feature work leaves code-related TODOs; annotate items as completed (strikethrough + date) when finished — do not delete
```

The trigger fires on any code change because every change is an opportunity to either log new deferred work or annotate previously tracked items as complete. The file is only modified when there is something to add or annotate — silence is the right outcome when no items are deferred and none reached completion.

## Version Management

After completing a major set of changes, offer to cut a new version. The full ritual: bump the version number, rotate the `upcoming.md` working files, commit, and tag.

### When to Offer

Offer a version bump after a coherent set of changes has settled — a feature, a bug fix, a refactor, a docs sweep, or any combination that the user clearly considers "done." Don't offer mid-flow, and don't offer for trivial in-isolation edits.

Don't bump the version yourself unless the user asks; phrase it as a question first ("Want me to cut v1.4.0 for this?").

### Choosing the Bump

Use a pragmatic, size-of-change framing rather than strict SemVer — bumps are scaled to the magnitude of the change set, with reverse-incompatibility as a contributing signal rather than the sole gate:

| Bump | Use for |
|------|---------|
| `patch` | The default for routine work — bug fixes, internal refactors, small features, doc updates, dependency bumps, and anything that doesn't merit a higher bump. |
| `minor` | Medium-sized change sets — substantial feature work, notable refactors, or related groups of changes shipped together. May include *some* reverse-incompatible changes when those are scoped and intentional. |
| `major` | Extremely large change sets — sweeping rewrites, broad reverse-incompatible work, or dropping support for a previously-supported platform/version. **Only when explicitly instructed by the user.** |

A single localized breaking change inside an otherwise medium-sized set of work is fine in a `minor`; a broad pattern of breaking changes across the codebase is a `major`. If you're unsure where a change set lands, ask the user before bumping.

### Step 1: Bump the version

The exact command or file depends on the project ecosystem. Use whatever the project uses to record its version, and bump every version-bearing file so they stay in sync.

| Ecosystem | How to bump |
|-----------|-------------|
| npm / pnpm / yarn | `npm version patch\|minor\|major` (or the equivalent `pnpm version` / `yarn version`) — updates `package.json` |
| Cargo (Rust) | Edit the `version` field in `Cargo.toml` |
| Python | Edit `pyproject.toml`, `setup.py`, or `__version__` (whichever the project uses) |
| Go modules | Tagging is the version source — no file edit; see Step 4 |
| Claude Code plugin | Edit `version` in both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` |
| Other / custom | Edit `version.txt`, a `VERSION` constant, or whatever the project's convention is |

If a project carries the version in multiple files, bump them together — a desynced version is its own kind of bug.

### Step 2: Rotate `upcoming.md` files

Rename both working files to versioned files:

```bash
git mv docs/release-notes/upcoming.md docs/release-notes/v{version}.md
git mv docs/changelogs/upcoming.md docs/changelogs/v{version}.md
```

Then create fresh empty `upcoming.md` files for subsequent work.

If the project uses a different layout, adapt: rotate whatever per-release working file the project keeps, then start a new one. Never lose content — every entry that was in `upcoming.md` belongs to the version being cut.

### Step 3: Commit

Stage the version bump and the rotated docs together so the versioned notes/changelog ship with the version. Match the project's commit-message style if it has one; otherwise:

```bash
git commit -m "chore(release): cut v{version}"
```

### Step 4: Tag the commit

```bash
git tag v{version}
```

Tag the version-bump commit itself — not an earlier or later commit. In many projects this tag triggers release and docs-deployment workflows; even where it doesn't, it gives readers a stable anchor for the release.

If the project pushes tags to a remote, ask the user before pushing — pushing a tag is publishing.

## Common Mistakes

These are the slips that recur across sessions; rules already covered in prose above (commit-hash format, release-notes-vs-changelog, tag-the-bump-commit, etc.) aren't repeated here.

| Mistake | Fix |
|---------|-----|
| Skipping doc updates under time pressure | Triggers are objective — evaluate them regardless of urgency |
| Treating `{Name}` in `Public-{Name}-API` as an exact path | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
| Forgetting one of multiple version-bearing files | When a project has e.g. `plugin.json` + `marketplace.json` or similar, bump all of them |
| Silently rotating `upcoming.md` during version cross-check | Tell the user what you found and confirm before renaming |
| Acting on a migration without explicit user agreement | The migration table lists *offers* — never execute one unilaterally |

## Subskills

| Doc | Scope |
|-----|-------|
| `docs/setup.md` | Creating a Documentation Sync section from scratch when a project doesn't have one (only loaded when the user asks to set one up) |
