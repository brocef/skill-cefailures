"""Analyze Claude Code permission request logs and group into patterns."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path

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


MAX_SAMPLES = 3


def _longest_common_prefix(token_lists: list[list[str]]) -> list[str]:
    """Find the longest common token prefix across all token lists."""
    if not token_lists:
        return []
    prefix = token_lists[0]
    for tokens in token_lists[1:]:
        length = min(len(prefix), len(tokens))
        cut = 0
        for i in range(length):
            if prefix[i] != tokens[i]:
                break
            cut = i + 1
        prefix = prefix[:cut]
        if not prefix:
            break
    return prefix


def _group_bash_commands(commands: list[str]) -> list[dict]:
    """Group a list of bash commands by longest common prefix.

    If the LCP across all commands is only one token and there are multiple
    distinct second tokens, sub-groups by the first two tokens to produce
    more specific patterns. Recurses until each group shares a meaningful prefix.
    """
    if not commands:
        return []

    token_lists = [cmd.split() for cmd in commands]
    prefix = _longest_common_prefix(token_lists)

    # If all commands share a prefix longer than 1 token, or there's only
    # one distinct next token (or only 1 command), emit the group directly
    all_covered = all(len(tl) == len(prefix) for tl in token_lists)

    if len(commands) == 1 or all_covered:
        prefix_str = " ".join(prefix)
        return [{
            "pattern": f"Bash({prefix_str})",
            "count": len(commands),
            "samples": commands[:MAX_SAMPLES],
        }]

    if len(prefix) >= 2:
        # Meaningful shared prefix of 2+ tokens; emit as wildcard group
        prefix_str = " ".join(prefix)
        return [{
            "pattern": f"Bash({prefix_str} *)",
            "count": len(commands),
            "samples": commands[:MAX_SAMPLES],
        }]

    # LCP is only 1 token (e.g. just "git") — sub-group by first 2 tokens
    by_two_tokens: dict[str, list[str]] = defaultdict(list)
    for cmd in commands:
        tokens = cmd.split()
        key = " ".join(tokens[:2]) if len(tokens) >= 2 else tokens[0]
        by_two_tokens[key].append(cmd)

    groups: list[dict] = []
    for _key, sub_cmds in by_two_tokens.items():
        groups.extend(_group_bash_commands(sub_cmds))
    return groups


def group_commands(entries: list[tuple[str, str]]) -> list[dict]:
    """Group parsed log entries into wildcard patterns.

    For Bash: splits compound commands, groups by first token, finds longest
    common prefix recursively. If the prefix covers all tokens, uses exact
    pattern; otherwise appends *. For non-Bash: groups by tool name as
    ToolName(*). Returns list of dicts with pattern, count, and samples (max 3).
    """
    bash_by_first_token: dict[str, list[str]] = defaultdict(list)
    non_bash_by_tool: dict[str, list[str]] = defaultdict(list)

    for tool, detail in entries:
        if tool == "Bash":
            sub_commands = split_compound_command(detail)
            for sub in sub_commands:
                tokens = sub.split()
                if tokens:
                    bash_by_first_token[tokens[0]].append(sub)
        else:
            non_bash_by_tool[tool].append(detail)

    groups: list[dict] = []

    for _first_token, commands in bash_by_first_token.items():
        groups.extend(_group_bash_commands(commands))

    for tool, details in non_bash_by_tool.items():
        groups.append({
            "pattern": f"{tool}(*)",
            "count": len(details),
            "samples": details[:MAX_SAMPLES],
        })

    return groups


def _is_subsumed(pattern: str, existing_rules: list[str]) -> bool:
    """Check if pattern is subsumed by any existing rule using glob matching.

    Extracts the inner content from ToolName(...) format and compares.
    Bash(git add *) is subsumed by Bash(git *) because fnmatch("git add *", "git *") is True.
    """
    for rule in existing_rules:
        if pattern == rule:
            return True
        # Extract tool and inner pattern from both
        if "(" not in pattern or "(" not in rule:
            continue
        p_tool = pattern[:pattern.index("(")]
        r_tool = rule[:rule.index("(")]
        if p_tool != r_tool:
            continue
        p_inner = pattern[pattern.index("(") + 1 : pattern.rindex(")")]
        r_inner = rule[rule.index("(") + 1 : rule.rindex(")")]
        if fnmatch(p_inner, r_inner):
            return True
    return False


def filter_groups(
    groups: list[dict], existing_rules: list[str]
) -> list[dict]:
    """Remove groups whose patterns are subsumed by existing rules.

    Uses fnmatch glob matching for subsumption: e.g., Bash(git *) subsumes
    Bash(git add *) because fnmatch("git add *", "git *") is True.
    """
    return [g for g in groups if not _is_subsumed(g["pattern"], existing_rules)]


AUDITOR_DIR = Path.home() / ".claude" / "permissions-auditor"
LOG_PATH = AUDITOR_DIR / "permission-requests.log"
CURSOR_PATH = AUDITOR_DIR / "cursor.txt"
MANUAL_PATH = AUDITOR_DIR / "manual-review-commands.txt"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


def _load_cursor(cursor_path: Path) -> int:
    """Load cursor (line offset) from file. Returns 0 if missing."""
    if cursor_path.exists():
        text = cursor_path.read_text().strip()
        if text.isdigit():
            return int(text)
    return 0


def _load_existing_rules(settings: dict, manual_path: Path) -> list[str]:
    """Collect all existing allow + deny + manual-review patterns."""
    perms = settings.get("permissions", {})
    rules = list(perms.get("allow", []))
    rules.extend(perms.get("deny", []))
    if manual_path.exists():
        for line in manual_path.read_text().splitlines():
            line = line.strip()
            if line:
                rules.append(line)
    return rules


def analyze(
    log_path: Path,
    cursor_path: Path,
    settings: dict,
    manual_path: Path,
) -> dict:
    """Analyze permission request log and return grouped patterns as a dict.

    Reads from cursor position, parses lines, groups commands,
    filters against existing rules, and returns JSON-serializable result.
    """
    if not log_path.exists():
        return {"groups": [], "total_new_lines": 0, "cursor": 0}

    lines = log_path.read_text().splitlines()
    total_lines = len(lines)
    cursor = _load_cursor(cursor_path)
    new_lines = lines[cursor:]

    entries: list[tuple[str, str]] = []
    for line in new_lines:
        parsed = parse_log_line(line)
        if parsed is None:
            if line.strip():
                print(f"Warning: skipping malformed line: {line!r}", file=sys.stderr)
            continue
        entries.append(parsed)

    groups = group_commands(entries)

    existing_rules = _load_existing_rules(settings, manual_path)
    groups = filter_groups(groups, existing_rules)

    groups.sort(key=lambda g: g["count"], reverse=True)

    return {
        "groups": groups,
        "total_new_lines": len(new_lines),
        "cursor": total_lines,
    }


def main() -> None:
    """CLI entry point: analyze log and print JSON to stdout."""
    if not SETTINGS_PATH.exists():
        settings: dict = {}
    else:
        settings = json.loads(SETTINGS_PATH.read_text())

    result = analyze(
        log_path=LOG_PATH,
        cursor_path=CURSOR_PATH,
        settings=settings,
        manual_path=MANUAL_PATH,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
