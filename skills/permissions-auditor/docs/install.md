# Install Permission Logging Hook

## Steps

1. **Check if already installed:**
   - Look for `~/.claude/hooks/log-permission-requests.sh`
   - If it exists, check whether it writes to `~/.claude/permissions-auditor/permission-requests.log` (new path) or `~/.claude/permission-requests.log` (old path)
   - If it writes to the old path, replace it with the new version

2. **Copy the hook script:**
   - Source: `scripts/log-permission-requests.sh` (relative to this repo's root — two directories up from this skill's `docs/` folder)
   - Destination: `~/.claude/hooks/log-permission-requests.sh`
   - Make it executable: `chmod +x ~/.claude/hooks/log-permission-requests.sh`

3. **Register the hook in settings.json:**
   - Read `~/.claude/settings.json`
   - Under `hooks.PermissionRequest`, add an entry if not already present:
     ```json
     {
       "matcher": ".*",
       "hooks": [
         {
           "type": "command",
           "command": "bash ~/.claude/hooks/log-permission-requests.sh"
         }
       ]
     }
     ```
   - Do not duplicate if an entry with the same `command` already exists

4. **Create the auditor directory:**
   - `mkdir -p ~/.claude/permissions-auditor`

5. **Migrate old log (if present):**
   - If `~/.claude/permission-requests.log` exists, ask the user if they'd like to move it:
     ```bash
     mv ~/.claude/permission-requests.log ~/.claude/permissions-auditor/permission-requests.log
     ```
   - If they decline, leave it. The new hook will write to the new location going forward.

## Verification

After installation, confirm:
- `~/.claude/hooks/log-permission-requests.sh` exists and is executable
- `~/.claude/settings.json` has the hook registered under `hooks.PermissionRequest`
- `~/.claude/permissions-auditor/` directory exists

Tell the user: "Hook installed. Permission requests will now be logged to `~/.claude/permissions-auditor/permission-requests.log`. Use this skill again to analyze the log once you've accumulated some data."
