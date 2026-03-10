#!/bin/bash
# Logs every Claude Code tool call that triggers a permission prompt.
# Review ~/.claude/permission-requests.log to find patterns worth adding
# to the "allow" list in ~/.claude/settings.json.
INPUT=$(cat)

TOOL=$(echo "$INPUT" | jq -r '.tool_name')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd')

if [ -n "$COMMAND" ]; then
  DETAIL="$COMMAND"
else
  DETAIL=$(echo "$INPUT" | jq -c '.tool_input')
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $TOOL | $DETAIL | CWD: $CWD" >> "$HOME/.claude/permission-requests.log"

exit 0
