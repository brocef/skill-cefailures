---
description: Cut a new version — choose the bump size, update every version-bearing file, rotate the upcoming.md working files, commit, and tag.
---

# Cut a New Version

Walk the user through the version-cut ritual: bump the version number, rotate the `upcoming.md` working files, commit, and tag.

## Choosing the Bump

Use a pragmatic, size-of-change framing rather than strict SemVer — bumps are scaled to the magnitude of the change set, with reverse-incompatibility as a contributing signal rather than the sole gate:

| Bump | Use for |
|------|---------|
| `patch` | The default for routine work — bug fixes, internal refactors, small features, doc updates, dependency bumps, and anything that doesn't merit a higher bump. |
| `minor` | Medium-sized change sets — substantial feature work, notable refactors, or related groups of changes shipped together. May include *some* reverse-incompatible changes when those are scoped and intentional. |
| `major` | Extremely large change sets — sweeping rewrites, broad reverse-incompatible work, or dropping support for a previously-supported platform/version. **Only when explicitly instructed by the user.** |

If the user selected "Micro version bump" from the `documentation-sync` skill's offer list, treat that as `patch` for ecosystems that use patch/minor/major terminology.

A single localized breaking change inside an otherwise medium-sized set of work is fine in a `minor`; a broad pattern of breaking changes across the codebase is a `major`. If you're unsure where a change set lands, ask the user before bumping.

## Step 1: Bump the version

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

## Step 2: Rotate `upcoming.md` files

Rename both working files to versioned files:

```bash
git mv docs/release-notes/upcoming.md docs/release-notes/v{version}.md
git mv docs/changelogs/upcoming.md docs/changelogs/v{version}.md
```

Then create fresh empty `upcoming.md` files for subsequent work.

If the project uses a different layout, adapt: rotate whatever per-release working file the project keeps, then start a new one. Never lose content — every entry that was in `upcoming.md` belongs to the version being cut.

## Step 3: Commit

Stage the version bump and the rotated docs together so the versioned notes/changelog ship with the version. Match the project's commit-message style if it has one; otherwise:

```bash
git commit -m "chore(release): cut v{version}"
```

## Step 4: Tag the commit

```bash
git tag v{version}
```

Tag the version-bump commit itself — not an earlier or later commit. In many projects this tag triggers release and docs-deployment workflows; even where it doesn't, it gives readers a stable anchor for the release.

If the project pushes tags to a remote, ask the user before pushing — pushing a tag is publishing.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgetting one of multiple version-bearing files | When a project has e.g. `plugin.json` + `marketplace.json` or similar, bump all of them |
| Tagging an earlier or later commit | Tag the version-bump commit itself |
| Pushing the tag without asking | Pushing a tag is publishing — confirm before `git push --tags` |
