---
description: Brain-style AGENTS.md review or authoring — checks for required sections, applies the minimal-routing principle, flags common bloat, and ensures CLAUDE.md is a symlink to AGENTS.md.
---

# AGENTS.md Style

Review the project's `AGENTS.md` (or help author a new one) against the conventions below. If the user has not pointed to a target file, ask which `AGENTS.md` they want reviewed.

## Canonical File and Symlinks

`AGENTS.md` is the canonical agent-instructions file — it's the cross-agent standard, read by Codex and other compatible agents. Claude Code reads `CLAUDE.md`, so **`CLAUDE.md` should be a symlink to `AGENTS.md`** rather than a second copy. This keeps one source of truth: edits to `AGENTS.md` are seen by every agent, and there's no drift between two files.

When reviewing or authoring, check the symlink:

```bash
# CLAUDE.md should point at AGENTS.md
ls -l CLAUDE.md   # -> CLAUDE.md -> AGENTS.md
```

If `CLAUDE.md` is a regular file (a duplicate) or missing, offer to fix it:

```bash
# Replace a duplicate (or create the link) — content lives in AGENTS.md
rm -f CLAUDE.md && ln -s AGENTS.md CLAUDE.md
```

Before deleting an existing `CLAUDE.md`, confirm its content is already in `AGENTS.md` — if it holds instructions that aren't, merge them into `AGENTS.md` first, then symlink. Every other agent's entrypoint follows the same pattern — symlink it to `AGENTS.md` so there's one source of truth: `GEMINI.md` (Gemini), `.github/copilot-instructions.md` (Copilot), `.cursorrules` (Cursor), and so on for whatever agents the project targets.

## Core Principle

An AGENTS.md file should be **minimal** — a routing file first, a reference file second. It is loaded into **every** session for **every** task, so it must carry only the bare essentials: the handful of facts and rules that apply to nearly any task in the project.

**Task-specific instruction does not belong in AGENTS.md.** Anything that only matters for a particular kind of work — a specific subsystem, a release procedure, an API's mechanics, a one-off workflow — lives in its own file, and AGENTS.md carries at most a short, keyword-rich pointer to it (the routing pattern). The test: if an instruction is irrelevant to most sessions, route it out. Inlining task-specific detail bloats the file, spends context every session pays for, and buries the essentials that actually apply everywhere.

As a rough ceiling, keep it **under ~150 lines** — a fresh file often starts at 20–30 and grows only as recurring mistakes prove a rule is worth inlining. If it's pushing past the ceiling, that's a signal to route content out, not to keep adding.

## Required Sections

Every project with an `AGENTS.md` should include the following sections. When reviewing or updating an `AGENTS.md`, check for each of these. If any are missing, offer to create them for the user — briefly explain what the section is for and ask if they'd like you to add it.

### Generic Instructions

General instructions that apply to most tasks in the project — behavioral preferences, commit message style, workflow rules, etc.

```markdown
## Generic Instructions

- Git commit messages should not include any co-authoring content
- Always run tests before committing
```

### Commands

Commonly used project-specific commands. Omit this section only if the project has no meaningful commands to document.

```markdown
## Commands

- `pnpm dev` — start development server
- `python -m pytest tests/ -v` — run all tests
- `./scripts/deploy.sh staging` — deploy to staging
```

### Coding Conventions

Naming rules, patterns, and idioms specific to the project. If the project uses a language covered by the `brain-style` skill (e.g. TypeScript — see `skills/brain-style/docs/typescript.md` in this plugin), auto-populate this section with the relevant conventions from that sub-style.

```markdown
## Coding Conventions

- kebab-case for file names
- PascalCase for enum members
- Prefix type parameters with `T`
```

### Documentation Sync

Trigger-based documentation update rules used by the `tcw:documentation-sync` skill (shipped by the TCW plugin). See `/tcw:tcw-docs-sync-setup` for how to create this section from scratch.

```markdown
## Documentation Sync

- `README.md` — update when: public API surface changes, new scripts are added
- `CHANGELOG.md` — update when: any user-facing change
```

## Inline vs. Route

**Inline when:**
- It applies to most tasks (commands, conventions, structure)
- There is no canonical source elsewhere
- It's short enough that routing would add more overhead than value

**Route when:**
- The information is defined in another file (README, docs, etc.)
- It only matters for a narrow subset of tasks
- It would duplicate content that has a canonical source
- **It is volatile** — it changes on an ordinary development cadence (a dependency bump, a refactor, a version cut, a feature shipping). Inline only facts that survive routine PRs; route everything that a normal change would invalidate to its canonical source.

Route format — include topic keywords so the agent can match the route without reading the target:

```markdown
For information about [topic keywords] see [section name] in [file path].
```

## Nested Files for Large Repos

The routing pattern also applies at the file-tree level. In a monorepo or a large project, don't grow one root file to cover every sub-project — put a `AGENTS.md` in the relevant subdirectory. Agents read the **nearest** `AGENTS.md` up the tree, so the root file carries only org-wide essentials and each subdirectory's file carries its local context.

```
repo/
  AGENTS.md            # org-wide essentials (apply everywhere)
  services/api/
    AGENTS.md          # context specific to the API service
  packages/ui/
    AGENTS.md          # context specific to the UI package
```

This keeps every file bare-essentials-only for its own scope, instead of one bloated file where most of the content is irrelevant to any given task. If the root file is accumulating per-subdirectory detail, that's the signal to split it downward.

## Keep It Stable (Anti-Volatility)

An AGENTS.md should rarely need editing. Before inlining a fact, ask: **"Would a routine PR make this line wrong?"** If yes, route it to where it's already maintained instead of copying it in. Specifically, do **not** inline:

| Volatile content | Route to / do instead |
|---|---|
| Exact dependency version pins (`^0.9.0`, `~54.0.34`, `next 16.2.2`) | Name the framework/major identity only if useful (e.g. "Expo SDK 54", "Next.js 16"); the exact pins live in `package.json`. |
| A "Status" / "current phase" / "what's shipped so far" section | Delete it — the repo's current state is in git history and the code, and a status line is stale the moment the next PR merges. |
| Deep file paths and line numbers that move on refactor (`src/app/view/[id]/[v]/contexts/...`) | Reference a stable directory or an exported symbol/function name, not a churning path. |
| Long operational or reference blocks only some tasks need (release checklists, per-endpoint API essays, per-env-var mechanics) | Move to a dedicated doc (e.g. a runbook, an architecture doc) and leave a keyword-rich routing pointer. |

## Never Inline Secrets

`AGENTS.md` is committed to the repo and should be treated as potentially public. Never inline credentials of any kind — API keys, tokens, passwords, connection strings with passwords, private keys. Document **where** a secret lives and **how** to fetch it, never its value:

```markdown
- `DATABASE_URL` — from AWS Secrets Manager (`prod/database`)
- `API_KEY` — from the `API_KEY` environment variable (set in deploy config)
```

## Recommended Directives

Certain directives provide enough value that they should appear in every project's AGENTS.md:

- **Bug workflow** — Include a directive like: *"When I report a bug, don't start by trying to fix it. Instead, start by writing a test that reproduces the bug. Then, use subagents to attempt fixes and prove them with a passing test."* This ensures bugs are understood before they are "fixed," prevents regressions, and leverages parallel subagents to explore solutions efficiently.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `CLAUDE.md` is a duplicate file, not a symlink | Merge any unique content into `AGENTS.md`, then replace `CLAUDE.md` with a symlink to it |
| Inlining a secret (key, token, connection string) | Never — document where it lives and how to fetch it |
| Omitting common commands | Inline these — they're needed for nearly every task |
| Inlining task-specific instructions | If it only matters for one subsystem/procedure/workflow, move it to its own file and leave a keyword-rich pointer |
| Making the file a comprehensive project wiki | Keep it minimal; route to existing docs |
| Routing to a section without topic keywords | Add keywords so the agent knows when to follow the route |
| Inlining exact dependency versions | They go stale on the next bump — name the major identity if needed, route exact pins to `package.json` |
| A "Status"/"current phase" section | Delete — inherently stale; state lives in git + code |
| Deep file paths / line numbers in prose | Reference stable directories or exported symbols instead |

## Sanity-Check the File

A quick test for whether the file earns its keep: could a fresh agent do a common task in the project using only `AGENTS.md` (plus the files it routes to)? If setting up, running tests, or following a convention requires knowledge that isn't in the file or reachable through one of its pointers, that gap is the next thing to add — and anything the agent never needed to read is a candidate to cut.
