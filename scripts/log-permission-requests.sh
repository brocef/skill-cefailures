#!/bin/bash
# Logs every Claude Code tool call that triggers a permission prompt.
# Install: copy to ~/.claude/hooks/log-permission-requests.sh
# Output: ~/.claude/permissions-auditor/permission-requests.log
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
