---
description: Brain-style CLAUDE.md review or authoring — checks for required sections, applies the minimal-routing principle, and flags common bloat.
---

# CLAUDE.md Style

Review the project's `CLAUDE.md` (or help author a new one) against the conventions below. If the user has not pointed to a target file, ask which `CLAUDE.md` they want reviewed.

## Core Principle

A CLAUDE.md file should be **minimal** — a routing file first, a reference file second. Only inline information that is generally useful for the average task performed in the project. Everything else should point to where the information already lives.

## Required Sections

Every project with a `CLAUDE.md` should include the following sections. When reviewing or updating a `CLAUDE.md`, check for each of these. If any are missing, offer to create them for the user — briefly explain what the section is for and ask if they'd like you to add it.

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

Trigger-based documentation update rules used by the `documentation-sync` skill. See `/skill-cefailures:documentation-sync:setup` for how to create this section from scratch.

```markdown
## Documentation Sync

- `README.md` — update when: public API surface changes, new scripts are added
- `CHANGELOG.md` — update when: any user-facing change
```

### Project Terminology

Project-specific terms that appear in the codebase or prompts and what they mean. This helps the agent understand domain language without guessing.

```markdown
## Project Terminology

- **EUsr** — end user
- **pvar** — propositional variable
- **CRD** — custom resource definition
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

## Keep It Stable (Anti-Volatility)

A CLAUDE.md should rarely need editing. Before inlining a fact, ask: **"Would a routine PR make this line wrong?"** If yes, route it to where it's already maintained instead of copying it in. Specifically, do **not** inline:

| Volatile content | Route to / do instead |
|---|---|
| Exact dependency version pins (`^0.9.0`, `~54.0.34`, `next 16.2.2`) | Name the framework/major identity only if useful (e.g. "Expo SDK 54", "Next.js 16"); the exact pins live in `package.json`. |
| A "Status" / "current phase" / "what's shipped so far" section | Delete it — the repo's current state is in git history and the code, and a status line is stale the moment the next PR merges. |
| Deep file paths and line numbers that move on refactor (`src/app/view/[id]/[v]/contexts/...`) | Reference a stable directory or an exported symbol/function name, not a churning path. |
| Long operational or reference blocks only some tasks need (release checklists, per-endpoint API essays, per-env-var mechanics) | Move to a dedicated doc (e.g. a runbook, an architecture doc) and leave a keyword-rich routing pointer. |

## Recommended Directives

Certain directives provide enough value that they should appear in every project's CLAUDE.md:

- **Bug workflow** — Include a directive like: *"When I report a bug, don't start by trying to fix it. Instead, start by writing a test that reproduces the bug. Then, use subagents to attempt fixes and prove them with a passing test."* This ensures bugs are understood before they are "fixed," prevents regressions, and leverages parallel subagents to explore solutions efficiently.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Omitting common commands | Inline these — they're needed for nearly every task |
| Making the file a comprehensive project wiki | Keep it minimal; route to existing docs |
| Routing to a section without topic keywords | Add keywords so the agent knows when to follow the route |
| Inlining exact dependency versions | They go stale on the next bump — name the major identity if needed, route exact pins to `package.json` |
| A "Status"/"current phase" section | Delete — inherently stale; state lives in git + code |
| Deep file paths / line numbers in prose | Reference stable directories or exported symbols instead |
