---
name: brain-style
description: Use when writing or reviewing code in any project. Use when making naming decisions for variables, constants, functions, or classes. Use when a linter flags naming conventions and you need to decide whether to fix or suppress. Use when fixing TypeScript type errors, lint warnings about types, or running a linter. Use when creating or updating a CLAUDE.md file. Use when the user asks for a "brain-review" of a file, function, class, or code unit.
---

# brain-style

Read the relevant doc based on your task:

| Sub-Style | Doc | Scope |
|-----------|-----|-------|
| TypeScript | `docs/typescript.md` | Naming conventions, casing rules, exemptions, type lint error fixing policy, and LSP usage |
| CLAUDE.md | `docs/claude-md.md` | Structure, inline vs. route decisions, required sections |
| Brain Review | `docs/brain-review.md` | Design architecture review — decomposition, file size, redundancy |

Does not cover formatting decisions handled by automated tools (Prettier, etc.).
