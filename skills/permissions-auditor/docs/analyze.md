# Analyze & Triage Permission Requests

## Prerequisites

- The permission logging hook must be installed (see `docs/install.md`)
- The log file at `~/.claude/permissions-auditor/permission-requests.log` should have accumulated entries

## Steps

1. **Locate the analysis script:**
   - This file lives at `skills/permissions-auditor/docs/analyze.md` — the repo root is three directories up from this file
   - The script is at `<repo-root>/scripts/analyze_permissions.py`

2. **Run the analysis:**
   ```bash
   python <repo-root>/scripts/analyze_permissions.py
   ```
   - The script outputs JSON to stdout

3. **Handle empty results:**
   - If `groups` is empty, tell the user: "All permission patterns have been triaged. No new patterns to review."
   - This can happen if there are no new log entries since last run, or all patterns are already covered by existing rules.

4. **Present results to the user:**
   - Show each group sorted by frequency (the script already sorts descending)
   - For each group, display:
     - The pattern (e.g., `Bash(git add *)`)
     - The count of occurrences
     - Up to 3 sample commands
   - Format as a numbered list for easy reference

5. **Triage each group:**
   - Present all groups and ask the user to decide for each:
     - **Allow** — will be added to `permissions.allow` in `~/.claude/settings.json`
     - **Deny** — will be added to `permissions.deny` in `~/.claude/settings.json`
     - **Keep Manual** — added to `~/.claude/permissions-auditor/manual-review-commands.txt` (won't be suggested again)
     - **Skip** — no action, will appear again on next run
   - The user may triage in bulk (e.g., "allow 1, 3, 5; deny 2; keep manual 4") or one at a time

6. **Apply changes:**
   - Read `~/.claude/settings.json`
   - Append allowed patterns to `permissions.allow` array (avoid duplicates)
   - Append denied patterns to `permissions.deny` array (avoid duplicates)
   - Write the updated settings back
   - Append keep-manual patterns to `~/.claude/permissions-auditor/manual-review-commands.txt` (one per line)
   - Write the new cursor value from the script output to `~/.claude/permissions-auditor/cursor.txt`

7. **Report summary:**
   - Tell the user what was added: "Added N patterns to allow, M to deny, K marked for manual review, J skipped."
