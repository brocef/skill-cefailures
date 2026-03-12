---
name: permissions-auditor
description: Use when managing Claude Code permission rules, analyzing permission request logs, installing the permission logging hook, or triaging allow/deny patterns in settings.json. Use when the user wants to reduce permission prompts or audit which commands require approval.
---

# Permissions Auditor

Analyze permission request logs to find recurring patterns, then triage them into allow/deny rules or mark them for continued manual review.

## When to Use

- User wants to install the permission logging hook
- User wants to analyze which commands are triggering permission prompts
- User wants to add commands to their allow or deny list
- User wants to audit or manage their permission rules

## Sub-Tasks

| Task | Doc | When |
|------|-----|------|
| Install Hook | `docs/install.md` | Setting up permission logging for the first time |
| Analyze & Triage | `docs/analyze.md` | Reviewing logged permissions and adding rules |
