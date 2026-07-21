---
name: brain-style
description: Use when writing or reviewing code in any project. Use when making naming decisions for variables, constants, functions, classes, or HTTP server routes. Use when adding or reviewing API endpoints and deciding between resource-oriented REST routes and action/instruction-style routes. Use when a linter flags naming conventions and you need to decide whether to fix or suppress. Use when fixing TypeScript type errors, lint warnings about types, or running a linter.
---

# brain-style

Code style preferences across naming and types.

| Doc | Scope |
|-----|-------|
| `docs/typescript.md` | Naming conventions, casing rules, exemptions, type lint error fixing policy, LSP usage |
| `docs/server-routes.md` | HTTP route design, resource-oriented REST defaults, action-style route exceptions |

## Companion commands

These workflows are explicit-invocation-only and live as slash commands, not as auto-triggered skill content:

- `/skill-cefailures:brain-style:review` — architecture review of a file/function/class against decomposition, file-size, and redundancy guidelines.
- `/skill-cefailures:brain-style:agents-md` — review or author a project's `AGENTS.md` against the minimal-routing principle and required-sections checklist, and ensure `CLAUDE.md` is a symlink to it.
