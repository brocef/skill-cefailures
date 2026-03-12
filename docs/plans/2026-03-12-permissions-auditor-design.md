# Permissions Auditor Skill — Design Spec

## Overview

A skill that helps users manage Claude Code permission rules by analyzing logged permission requests, grouping them into wildcard patterns, and letting the user triage them into allow/deny/manual-review categories.

## Motivation

Claude Code prompts users to approve or deny tool calls that aren't covered by `settings.json` allow/deny rules. Over time, the same patterns recur. This skill automates the process of identifying those patterns and adding them to the appropriate list, reducing friction while preserving control over commands the user wants to review each time.

## File Layout

### In repo

```
skills/permissions-auditor/
  SKILL.md                          # Routing layer
  docs/
    install.md                      # Hook installation instructions
    analyze.md                      # Analysis and triage workflow
scripts/
  analyze_permissions.py            # Log parser and grouper
  log-permission-requests.sh        # Hook script (install source)
```

This skill replaces the existing `plugins/log-permission-requests/` directory. As part of this work:
- Remove `plugins/log-permission-requests/` (hook script and plugin.json)
- Remove `scripts/install_plugin.py` (no remaining plugins to manage)
- Remove the `plugins/` directory entirely if empty
- Update CLAUDE.md to remove references to `install_plugin.py` and the plugins directory

### On user's machine

```
~/.claude/settings.json                              # allow/deny rules (existing)
~/.claude/hooks/log-permission-requests.sh            # copy of hook script
~/.claude/permissions-auditor/
  permission-requests.log                            # raw log (written by hook)
  manual-review-commands.txt                         # commands user wants to keep manual
  cursor.txt                                         # last-processed line number
```

## Components

### 1. Hook Script (`scripts/log-permission-requests.sh`)

Logs every permission request to `~/.claude/permissions-auditor/permission-requests.log`.

```bash
#!/bin/bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd')

if [ -n "$COMMAND" ]; then
  DETAIL="$COMMAND"
else
  DETAIL=$(echo "$INPUT" | jq -c '.tool_input')
fi

mkdir -p "$HOME/.claude/permissions-auditor"
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $TOOL | $DETAIL | CWD: $CWD" >> "$HOME/.claude/permissions-auditor/permission-requests.log"
exit 0
```

Installed as `~/.claude/hooks/log-permission-requests.sh` (copy from `scripts/`). Registered in `settings.json` under `hooks.PermissionRequest` with matcher `".*"`.

### 2. Analysis Script (`scripts/analyze_permissions.py`)

**Reads:**
- `~/.claude/permissions-auditor/permission-requests.log` — raw log entries
- `~/.claude/permissions-auditor/cursor.txt` — line offset from last run (0 if absent)
- `~/.claude/settings.json` — existing allow/deny patterns
- `~/.claude/permissions-auditor/manual-review-commands.txt` — user-designated manual-review patterns

**Processing:**
1. Capture cursor value (line count) at read time, before processing, so lines appended during analysis don't cause inconsistency
2. Read log from cursor position to end of file
3. Parse each line into `(tool, detail)` tuples; skip malformed lines (missing `|` delimiter, empty lines) with a warning to stderr
4. For Bash entries: compute longest common prefix groups across commands, producing patterns like `git add *`, `python -m pytest *`
5. For non-Bash entries (Edit, Read, etc.): group by tool name — `Edit(*)`, `Read(*)`
6. Wrap each group in the `ToolName(pattern)` format to match settings.json conventions
7. Filter out groups that are subsumed by an existing allow rule, deny rule, or manual-review entry (using glob matching, not exact string comparison)
8. Sort remaining groups by frequency descending

**Output (JSON to stdout):**
```json
{
  "groups": [
    {
      "pattern": "Bash(python -m pytest *)",
      "count": 42,
      "samples": [
        "python -m pytest tests/ -v",
        "python -m pytest tests/test_foo.py"
      ]
    },
    {
      "pattern": "Edit(*)",
      "count": 15,
      "samples": [
        "{\"file_path\": \"/some/path\"}"
      ]
    }
  ],
  "total_new_lines": 187,
  "cursor": 1527
}
```

**Longest common prefix grouping algorithm:**
- Tokenize each Bash command by whitespace
- Group commands that share the same first token
- Within each first-token group, find the longest common token prefix across all commands
- For groups with 2+ commands: the pattern is the common prefix tokens joined by spaces, followed by `*`
- For singleton commands (only seen once): use the full command as the pattern with no trailing `*` (e.g., `Bash(brew install jq)`)
- Example: `git add src/foo.ts` and `git add src/bar.ts` → prefix `git add` → pattern `git add *`
- Example: `python -m pytest tests/ -v` and `python -m pytest tests/test_foo.py` → prefix `python -m pytest` → pattern `python -m pytest *`

**Filtering logic:**
- A group is filtered if its `ToolName(pattern)` is subsumed by any existing allow rule, deny rule, or manual-review entry
- Subsumption uses glob matching: `Bash(git *)` subsumes `Bash(git add *)` because `git *` matches `git add *`
- This prevents suggesting patterns the user has already covered with a broader rule

**Samples limit:** Each group includes at most 3 sample commands from the log.

### 3. Skill — SKILL.md

Routing layer with frontmatter:

```yaml
---
name: permissions-auditor
description: Use when managing Claude Code permission rules, analyzing permission request logs, installing the permission logging hook, or triaging allow/deny patterns in settings.json. Use when the user wants to reduce permission prompts or audit which commands require approval.
---
```

Routes to:
- `docs/install.md` — when user needs to set up the hook
- `docs/analyze.md` — when user wants to analyze and triage permissions

### 4. Skill — docs/install.md

Instructions for Claude to:
1. Check if `~/.claude/hooks/log-permission-requests.sh` already exists
2. If not, copy `scripts/log-permission-requests.sh` to `~/.claude/hooks/log-permission-requests.sh`
3. Make it executable
4. Register the hook in `~/.claude/settings.json` under `hooks.PermissionRequest` with matcher `".*"`
5. Create `~/.claude/permissions-auditor/` directory
6. If `~/.claude/permission-requests.log` exists (old location), offer to move it to the new location

### 5. Skill — docs/analyze.md

Instructions for Claude to:
1. Determine the repo root by navigating from the skill's own path (the skill lives at `skills/permissions-auditor/`, so the repo root is two levels up; the script is at `scripts/analyze_permissions.py` relative to the repo root)
2. Run `python <repo-root>/scripts/analyze_permissions.py`
3. If no groups returned, inform the user everything is triaged
4. Present groups sorted by frequency, showing count and up to 3 sample commands
5. For each group (or in bulk), ask the user to choose:
   - **Allow** — add to `permissions.allow` in `settings.json`
   - **Deny** — add to `permissions.deny` in `settings.json`
   - **Keep Manual** — append to `~/.claude/permissions-auditor/manual-review-commands.txt`
   - **Skip** — leave for next time
6. After triage:
   - Update `settings.json` with new allow/deny entries
   - Append keep-manual entries to `manual-review-commands.txt`
   - Write new cursor value to `cursor.txt`

## Data Flow

```
Permission Request → Hook Script → permission-requests.log
                                          ↓
                                  analyze_permissions.py
                                   ↓           ↓           ↓
                              reads log    reads cursor   reads settings + manual-review
                                   ↓
                              groups & filters
                                   ↓
                              JSON to stdout
                                   ↓
                              Claude presents to user
                                   ↓
                              User triages (allow/deny/manual/skip)
                                   ↓
                              Claude updates settings.json, manual-review, cursor
```

## Testing

A corresponding `tests/test_analyze_permissions.py` should be created with pytest, covering:
- Log line parsing (valid and malformed lines)
- Longest common prefix grouping (multi-command groups, singletons, edge cases)
- Filtering against existing allow/deny/manual-review rules (including glob subsumption)
- Cursor-based incremental reading
- JSON output format
