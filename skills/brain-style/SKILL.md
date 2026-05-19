---
name: brain-style
description: Use when writing or reviewing code in any project. Use when making naming decisions for variables, constants, functions, or classes. Use when a linter flags naming conventions and you need to decide whether to fix or suppress. Use when fixing TypeScript type errors, lint warnings about types, or running a linter.
---

# brain-style

Code style preferences across naming and types.

| Doc | Scope |
|-----|-------|
| `docs/typescript.md` | Naming conventions, casing rules, exemptions, type lint error fixing policy, LSP usage |

## Companion commands

These workflows are explicit-invocation-only and live as slash commands, not as auto-triggered skill content:

- `/skill-cefailures:brain-style:review` — architecture review of a file/function/class against decomposition, file-size, and redundancy guidelines.
- `/skill-cefailures:brain-style:claude-md` — review or author a project's `CLAUDE.md` against the minimal-routing principle and required-sections checklist.
