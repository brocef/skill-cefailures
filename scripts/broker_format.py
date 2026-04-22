#!/usr/bin/env python3
"""Line-oriented message display format for the DM broker.

    <ISO8601> [<sender>] <content>                                 # single recipient (inbox context)
    <ISO8601> [<sender> → <recipient>, <recipient>] <content>      # multi-recipient; viewer appears as 'you'
    <ISO8601> [<sender> → BROADCAST] <content>                     # broadcast
"""

import re
from dataclasses import dataclass


_LINE_RE = re.compile(r"^(\S+)\s+\[([^\]]+)\]\s+(.*)$")


@dataclass
class ParsedMessage:
    timestamp: str
    sender: str
    recipients: list[str]
    is_broadcast: bool
    content: str


def escape_content(content: str) -> str:
    """Encode a message body so it fits on one line. Backslashes first, then newlines."""
    return content.replace("\\", "\\\\").replace("\n", "\\n")


def unescape_content(escaped: str) -> str:
    """Inverse of escape_content. Decodes `\\n` -> newline and `\\\\` -> `\\`."""
    result = []
    i = 0
    while i < len(escaped):
        ch = escaped[i]
        if ch == "\\" and i + 1 < len(escaped):
            nxt = escaped[i + 1]
            if nxt == "n":
                result.append("\n")
                i += 2
                continue
            if nxt == "\\":
                result.append("\\")
                i += 2
                continue
        result.append(ch)
        i += 1
    return "".join(result)


def format_message(
    timestamp: str,
    sender: str,
    recipients: list[str],
    content: str,
    viewer: str,
) -> str:
    """Render a message as a single display line for the given viewer."""
    escaped = escape_content(content)
    if recipients == ["BROADCAST"]:
        return f"{timestamp} [{sender} → BROADCAST] {escaped}"
    if len(recipients) == 1 and recipients[0] == viewer:
        return f"{timestamp} [{sender}] {escaped}"
    rendered = [("you" if r == viewer else r) for r in recipients]
    return f"{timestamp} [{sender} → {', '.join(rendered)}] {escaped}"


def parse_message(line: str, viewer: str) -> ParsedMessage:
    """Parse a display line back into its components. `viewer` resolves the `you` alias."""
    match = _LINE_RE.match(line)
    if not match:
        raise ValueError(f"Malformed message line: {line!r}")
    timestamp, meta, raw_content = match.group(1), match.group(2), match.group(3)
    content = unescape_content(raw_content)
    if " → " in meta:
        sender, recipient_part = meta.split(" → ", 1)
        if recipient_part == "BROADCAST":
            return ParsedMessage(timestamp, sender, ["BROADCAST"], True, content)
        recipients = [r.strip() for r in recipient_part.split(",")]
        recipients = [viewer if r == "you" else r for r in recipients]
        return ParsedMessage(timestamp, sender, recipients, False, content)
    return ParsedMessage(timestamp, meta, [viewer], False, content)
