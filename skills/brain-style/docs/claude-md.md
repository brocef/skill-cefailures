# CLAUDE.md Style

## Core Principle

A CLAUDE.md file should be **minimal** — a routing file first, a reference file second. Only inline information that is generally useful for the average task performed in the project. Everything else should point to where the information already lives.

## What to Inline

Content that provides clear, generalized value for most tasks:

- **Common commands** — installing dependencies, linting, running tests, building
- **Code conventions** — naming rules, patterns, idioms specific to the project
- **Documentation Sync section** — trigger-based doc update rules
- **Architecture notes** — brief structural overview (tech stack, key directories)
- **Generic instructions** — behavioral preferences (e.g., commit message style)

## What to Route

Content that is only relevant to specific tasks or already exists elsewhere:

```markdown
# Instead of re-declaring project terms:
For information about the Widget Pipeline, see "Architecture" in README.md.

# Instead of duplicating API docs:
For API endpoint details, see docs/api.md.

# Instead of copying onboarding steps:
For environment setup, see "Getting Started" in README.md.
```

**Route when:**
- The information is defined in another file (README, docs, etc.)
- It only matters for a narrow subset of tasks
- It would duplicate content that has a canonical source

**Inline when:**
- It applies to most tasks (commands, conventions, structure)
- There is no canonical source elsewhere
- It's short enough that routing would add more overhead than value

## Routing Format

Use a concise pointer with enough context for the agent to decide whether to follow it:

```markdown
For information about [topic keywords] see [section name] in [file path].
```

Include topic keywords so the agent can match the route to its current task without reading the target file.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Duplicating README content into CLAUDE.md | Route to the README section instead |
| Including setup instructions that live in a guide | Point to the guide |
| Omitting common commands | Inline these — they're needed for nearly every task |
| Making the file a comprehensive project wiki | Keep it minimal; route to existing docs |
| Routing to a section without topic keywords | Add keywords so the agent knows when to follow the route |
