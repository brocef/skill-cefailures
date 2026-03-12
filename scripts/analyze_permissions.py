"""Analyze Claude Code permission request logs and group into patterns."""

from __future__ import annotations

import re
import sys

# Shell operators that separate independent sub-commands
_SHELL_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||\||;)\s*")


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


def split_compound_command(command: str) -> list[str]:
    """Split a compound Bash command into individual sub-commands.

    Splits on &&, ||, |, and ; operators. Strips whitespace, filters
    empty results and comment lines. Also splits on newlines since
    multi-line commands appear in logs.
    """
    # First split on newlines, then on shell operators
    parts: list[str] = []
    for line in command.split("\n"):
        parts.extend(_SHELL_SPLIT_RE.split(line))

    return [
        p.strip() for p in parts
        if p.strip() and not p.strip().startswith("#")
    ]


if __name__ == "__main__":
    pass
