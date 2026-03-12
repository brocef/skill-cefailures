"""Analyze Claude Code permission request logs and group into patterns."""

from __future__ import annotations

import sys


def parse_log_line(line: str) -> tuple[str, str] | None:
    """Parse a log line into (tool, detail). Returns None for malformed lines.

    Format: [timestamp] Tool | Detail | CWD: /path
    The detail field may itself contain pipe characters (e.g. bash piped commands),
    so we split on ' | ' and treat the first segment after timestamp as tool,
    the last segment as CWD, and everything in between as detail.
    """
    line = line.strip()
    if not line or " | " not in line:
        return None

    parts = line.split(" | ")
    if len(parts) < 3:
        return None

    # First part: "[timestamp] Tool"
    first = parts[0]
    bracket_end = first.find("] ")
    if bracket_end == -1:
        return None
    tool = first[bracket_end + 2:].strip()

    # Last part: "CWD: /path"
    # Everything in between is the detail (may contain pipes)
    detail = " | ".join(parts[1:-1]).strip()

    if not tool or not detail:
        return None

    return (tool, detail)


if __name__ == "__main__":
    pass
