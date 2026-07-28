---
name: report
description: Use when reporting a bug, issue, or suggestion about the skill-cefailures plugin itself — a skill giving wrong guidance, a `/skill-cefailures:*` slash command misfiring, a `create_skill.py` failure, or a feature request. Files a GitHub issue on this repo and provides a ready-to-fill skeleton for each report kind. Not for bugs in the user's own project.
---

# Reporting an issue or suggestion to skill-cefailures

Feedback about **the plugin itself** — a skill that gives wrong guidance, a slash
command that misfires, a `create_skill.py` failure, a feature idea —
goes to the project's issue tracker on GitHub.

**File it here:** https://github.com/brocef/skill-cefailures/issues

## Before filing

1. **Search first.** Skim the open (and recently closed) issues for the same
   symptom or idea; if one exists, add your detail there instead of opening a
   duplicate.
2. **Pick the kind:** a **bug** (something is broken or behaves wrong) or a
   **suggestion / feature** (something should exist or work differently). Use the
   matching skeleton below.
3. **Name the surface.** This plugin ships several, and they fail differently —
   say which one you hit:
   - a **skill** (`skills/<name>/`, e.g. `brain-style`, `capabilities-sdlc`, `report`)
   - a **slash command** (`/skill-cefailures:<group>:<action>`)
   - the **skill-generation tooling** (`scripts/create_skill.py`)
4. **Grab the version.** For a bug, include the `version` field from
   `.claude-plugin/plugin.json` in your installed copy.
5. **Say which agent.** The plugin targets both Claude Code and Codex, and a bug
   often only reproduces on one. Note which you were running.

## Bug skeleton

```markdown
**Title:** <one line: what breaks, where>

### Environment
- Plugin version: <`version` in .claude-plugin/plugin.json>
- Surface: <skill name / slash command / create_skill.py>
- Agent: <Claude Code / Codex — and its version>
- OS / platform: <e.g. macOS 14, Ubuntu 24.04>

### Steps to reproduce
1. <exact prompt, command, or action>
2. <...>
3. <...>

### Expected vs. actual
- Expected: <what should have happened>
- Actual: <what happened — paste the error, output, or the guidance verbatim>

### Remediation
<proposed fix, workaround you found, or "unknown — needs investigation">
```

## Suggestion / feature skeleton

```markdown
**Title:** <one line: the change you want>

### Motivation
<the problem or friction today — why the status quo falls short>

### Description
<what you are proposing, concretely — the skill, command, wording, or behavior>

### Benefits
<who it helps and how; what it unlocks or simplifies>
```

Keep it concrete: a real prompt, a real error, a real scenario beats an abstract
description. For a skill that gave wrong or stale guidance, quote the passage and
say what the library actually does — that turns the report straight into a fix.
For anything touching a skill or command, note whether it affects Claude Code,
Codex, or both.
