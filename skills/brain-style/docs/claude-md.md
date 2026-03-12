# CLAUDE.md Style

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

Naming rules, patterns, and idioms specific to the project. If the project uses a language covered by this skill's sub-styles (e.g. TypeScript — see `docs/typescript.md`), auto-populate this section with the relevant conventions from that sub-style.

```markdown
## Coding Conventions

- kebab-case for file names
- PascalCase for enum members
- Prefix type parameters with `T`
```

### Documentation Sync

Trigger-based documentation update rules used by the `documentation-sync` skill. See that skill's `docs/setup.md` for how to create this section from scratch.

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

Route format — include topic keywords so the agent can match the route without reading the target:

```markdown
For information about [topic keywords] see [section name] in [file path].
```

## Recommended Directives

Certain directives provide enough value that they should appear in every project's CLAUDE.md:

- **Bug workflow** — Include a directive like: *"When I report a bug, don't start by trying to fix it. Instead, start by writing a test that reproduces the bug. Then, use subagents to attempt fixes and prove them with a passing test."* This ensures bugs are understood before they are "fixed," prevents regressions, and leverages parallel subagents to explore solutions efficiently.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Omitting common commands | Inline these — they're needed for nearly every task |
| Making the file a comprehensive project wiki | Keep it minimal; route to existing docs |
| Routing to a section without topic keywords | Add keywords so the agent knows when to follow the route |
