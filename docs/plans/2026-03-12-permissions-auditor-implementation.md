# Permissions Auditor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a skill that analyzes permission request logs, groups them into wildcard patterns, and lets users triage them into allow/deny/manual-review.

**Architecture:** A Python analysis script handles log parsing, LCP grouping, and filtering. Skill markdown files instruct Claude how to install the hook, run the script, present results, and update settings. The existing `plugins/log-permission-requests/` infrastructure is replaced.

**Tech Stack:** Python 3 (pytest, `fnmatch`), Bash (hook script), Markdown (skill files)

**Spec:** `docs/plans/2026-03-12-permissions-auditor-design.md`

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scripts/analyze_permissions.py` | Parse log, group by LCP, filter, output JSON |
| Create | `scripts/log-permission-requests.sh` | Hook script — logs permission requests |
| Create | `skills/permissions-auditor/SKILL.md` | Routing layer |
| Create | `skills/permissions-auditor/docs/install.md` | Hook installation instructions |
| Create | `skills/permissions-auditor/docs/analyze.md` | Analysis and triage workflow |
| Create | `tests/test_analyze_permissions.py` | Tests for the analysis script |
| Delete | `plugins/log-permission-requests/log-permission-requests.sh` | Replaced by `scripts/` copy |
| Delete | `plugins/log-permission-requests/plugin.json` | No longer needed |
| Delete | `scripts/install_plugin.py` | No remaining plugins |
| Modify | `CLAUDE.md` | Remove plugin references, add permissions-auditor references |

---

## Chunk 1: Analysis Script Core

### Task 1: Log line parser

**Files:**
- Create: `scripts/analyze_permissions.py`
- Create: `tests/test_analyze_permissions.py`

- [ ] **Step 1: Write failing tests for log line parsing**

```python
# tests/test_analyze_permissions.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_permissions import parse_log_line


def test_parse_bash_line():
    """Parse a Bash command log line."""
    line = "[2026-03-11T00:13:20Z] Bash | git log --oneline -5 | CWD: /some/path"
    result = parse_log_line(line)
    assert result == ("Bash", "git log --oneline -5")


def test_parse_edit_line():
    """Parse a non-Bash (JSON detail) log line."""
    line = '[2026-03-11T00:14:26Z] Edit | {"file_path":"/some/file.ts","old_string":"a","new_string":"b","replace_all":false} | CWD: /some/path'
    result = parse_log_line(line)
    assert result == ("Edit", '{"file_path":"/some/file.ts","old_string":"a","new_string":"b","replace_all":false}')


def test_parse_malformed_line_returns_none():
    """Malformed lines (no pipe delimiter) return None."""
    assert parse_log_line("this is garbage") is None
    assert parse_log_line("") is None


def test_parse_line_with_pipe_in_command():
    """Bash commands containing | should preserve the middle pipes."""
    line = "[2026-03-11T00:13:20Z] Bash | echo hello | grep hello | CWD: /some/path"
    result = parse_log_line(line)
    assert result == ("Bash", "echo hello | grep hello")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analyze_permissions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analyze_permissions'`

- [ ] **Step 3: Implement parse_log_line**

```python
# scripts/analyze_permissions.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analyze_permissions.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_permissions.py tests/test_analyze_permissions.py
git commit -m "Add log line parser for permissions auditor"
```

---

### Task 2: Longest common prefix grouping

**Files:**
- Modify: `scripts/analyze_permissions.py`
- Modify: `tests/test_analyze_permissions.py`

- [ ] **Step 1: Write failing tests for LCP grouping**

```python
# append to tests/test_analyze_permissions.py
from analyze_permissions import group_commands


def test_group_bash_commands_shared_prefix():
    """Commands sharing a prefix get grouped with wildcard."""
    entries = [
        ("Bash", "git add src/foo.ts"),
        ("Bash", "git add src/bar.ts"),
        ("Bash", "git add src/baz.ts"),
    ]
    groups = group_commands(entries)
    assert len(groups) == 1
    assert groups[0]["pattern"] == "Bash(git add *)"
    assert groups[0]["count"] == 3
    assert len(groups[0]["samples"]) <= 3


def test_group_bash_commands_deeper_prefix():
    """LCP should find the longest shared prefix, not just first token."""
    entries = [
        ("Bash", "python -m pytest tests/ -v"),
        ("Bash", "python -m pytest tests/test_foo.py"),
    ]
    groups = group_commands(entries)
    assert len(groups) == 1
    assert groups[0]["pattern"] == "Bash(python -m pytest *)"


def test_group_bash_singleton():
    """A command seen only once uses full command, no wildcard."""
    entries = [
        ("Bash", "brew install jq"),
    ]
    groups = group_commands(entries)
    assert len(groups) == 1
    assert groups[0]["pattern"] == "Bash(brew install jq)"
    assert groups[0]["count"] == 1


def test_group_bash_different_first_tokens():
    """Commands with different first tokens form separate groups."""
    entries = [
        ("Bash", "git add file.ts"),
        ("Bash", "git add other.ts"),
        ("Bash", "npm run build"),
        ("Bash", "npm run test"),
    ]
    groups = group_commands(entries)
    patterns = {g["pattern"] for g in groups}
    assert "Bash(git add *)" in patterns
    assert "Bash(npm run *)" in patterns


def test_group_non_bash_by_tool():
    """Non-Bash entries are grouped by tool name as ToolName(*)."""
    entries = [
        ("Edit", '{"file_path":"a.ts"}'),
        ("Edit", '{"file_path":"b.ts"}'),
        ("Read", '{"file_path":"c.ts"}'),
    ]
    groups = group_commands(entries)
    patterns = {g["pattern"] for g in groups}
    assert "Edit(*)" in patterns
    assert "Read(*)" in patterns


def test_group_mixed_bash_and_non_bash():
    """Bash and non-Bash entries are grouped independently."""
    entries = [
        ("Bash", "git add file.ts"),
        ("Bash", "git add other.ts"),
        ("Edit", '{"file_path":"a.ts"}'),
    ]
    groups = group_commands(entries)
    patterns = {g["pattern"] for g in groups}
    assert "Bash(git add *)" in patterns
    assert "Edit(*)" in patterns


def test_group_repeated_identical_commands():
    """Identical commands repeated should use exact pattern, no trailing *."""
    entries = [
        ("Bash", "python -m pytest tests/ -v"),
        ("Bash", "python -m pytest tests/ -v"),
        ("Bash", "python -m pytest tests/ -v"),
    ]
    groups = group_commands(entries)
    assert len(groups) == 1
    assert groups[0]["pattern"] == "Bash(python -m pytest tests/ -v)"
    assert groups[0]["count"] == 3


def test_group_samples_capped_at_three():
    """Samples should contain at most 3 entries."""
    entries = [("Bash", f"git add file{i}.ts") for i in range(10)]
    groups = group_commands(entries)
    assert len(groups[0]["samples"]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analyze_permissions.py::test_group_bash_commands_shared_prefix -v`
Expected: FAIL — `ImportError: cannot import name 'group_commands'`

- [ ] **Step 3: Implement group_commands**

```python
# add to scripts/analyze_permissions.py

from collections import defaultdict

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


def group_commands(entries: list[tuple[str, str]]) -> list[dict]:
    """Group parsed log entries into wildcard patterns.

    For Bash: group by first token, find longest common prefix. If the prefix
    covers all tokens in every command, use the exact command; otherwise append *.
    For non-Bash: group by tool name as ToolName(*).
    Returns list of dicts with pattern, count, and samples (max 3).
    """
    bash_by_first_token: dict[str, list[str]] = defaultdict(list)
    non_bash_by_tool: dict[str, list[str]] = defaultdict(list)

    for tool, detail in entries:
        if tool == "Bash":
            tokens = detail.split()
            if tokens:
                bash_by_first_token[tokens[0]].append(detail)
        else:
            non_bash_by_tool[tool].append(detail)

    groups = []

    for _first_token, commands in bash_by_first_token.items():
        token_lists = [cmd.split() for cmd in commands]
        prefix = _longest_common_prefix(token_lists)
        prefix_str = " ".join(prefix)

        # If the prefix covers every token of every command, use exact pattern
        all_covered = all(len(tl) == len(prefix) for tl in token_lists)
        if len(commands) == 1 or all_covered:
            pattern = f"Bash({prefix_str})"
        else:
            pattern = f"Bash({prefix_str} *)"

        groups.append({
            "pattern": pattern,
            "count": len(commands),
            "samples": commands[:MAX_SAMPLES],
        })

    for tool, details in non_bash_by_tool.items():
        groups.append({
            "pattern": f"{tool}(*)",
            "count": len(details),
            "samples": details[:MAX_SAMPLES],
        })

    return groups
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analyze_permissions.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_permissions.py tests/test_analyze_permissions.py
git commit -m "Add LCP grouping logic for permissions auditor"
```

---

### Task 3: Glob-based filtering

**Files:**
- Modify: `scripts/analyze_permissions.py`
- Modify: `tests/test_analyze_permissions.py`

- [ ] **Step 1: Write failing tests for filter_groups**

```python
# append to tests/test_analyze_permissions.py
from analyze_permissions import filter_groups


def test_filter_exact_match():
    """Group matching an existing rule exactly is filtered out."""
    groups = [{"pattern": "Bash(git add *)", "count": 5, "samples": []}]
    existing = ["Bash(git add *)"]
    result = filter_groups(groups, existing)
    assert result == []


def test_filter_subsumed_by_broader_rule():
    """Bash(git add *) is subsumed by Bash(git *)."""
    groups = [{"pattern": "Bash(git add *)", "count": 5, "samples": []}]
    existing = ["Bash(git *)"]
    result = filter_groups(groups, existing)
    assert result == []


def test_filter_not_subsumed():
    """Bash(npm run *) is NOT subsumed by Bash(git *)."""
    groups = [{"pattern": "Bash(npm run *)", "count": 5, "samples": []}]
    existing = ["Bash(git *)"]
    result = filter_groups(groups, existing)
    assert len(result) == 1


def test_filter_non_bash_subsumed():
    """Edit(*) in existing rules filters out Edit(*) group."""
    groups = [{"pattern": "Edit(*)", "count": 3, "samples": []}]
    existing = ["Edit(*)"]
    result = filter_groups(groups, existing)
    assert result == []


def test_filter_combines_allow_deny_manual():
    """Filtering checks allow, deny, and manual-review lists together."""
    groups = [
        {"pattern": "Bash(git add *)", "count": 5, "samples": []},
        {"pattern": "Bash(git push *)", "count": 2, "samples": []},
        {"pattern": "Bash(npm run *)", "count": 3, "samples": []},
    ]
    existing = ["Bash(git add *)", "Bash(git push *)"]
    result = filter_groups(groups, existing)
    assert len(result) == 1
    assert result[0]["pattern"] == "Bash(npm run *)"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analyze_permissions.py::test_filter_exact_match -v`
Expected: FAIL — `ImportError: cannot import name 'filter_groups'`

- [ ] **Step 3: Implement filter_groups**

```python
# add to scripts/analyze_permissions.py
from fnmatch import fnmatch


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analyze_permissions.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_permissions.py tests/test_analyze_permissions.py
git commit -m "Add glob-based filtering for permissions auditor"
```

---

### Task 4: Main entry point (cursor, file I/O, JSON output)

**Files:**
- Modify: `scripts/analyze_permissions.py`
- Modify: `tests/test_analyze_permissions.py`

- [ ] **Step 1: Write failing tests for the main analysis function**

```python
# append to tests/test_analyze_permissions.py
import json


def test_analyze_full_pipeline(tmp_path):
    """End-to-end: log file -> JSON output with groups, cursor."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | git add src/foo.ts | CWD: /path\n"
        "[2026-03-11T00:13:21Z] Bash | git add src/bar.ts | CWD: /path\n"
        "[2026-03-11T00:13:22Z] Edit | {\"file_path\":\"/a.ts\"} | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    settings = {"permissions": {"allow": [], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    assert result["total_new_lines"] == 3
    assert result["cursor"] == 3
    patterns = {g["pattern"] for g in result["groups"]}
    assert "Bash(git add *)" in patterns
    assert "Edit(*)" in patterns


def test_analyze_respects_cursor(tmp_path):
    """Only lines after the cursor are processed."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | git add old.ts | CWD: /path\n"
        "[2026-03-11T00:13:21Z] Bash | git add new.ts | CWD: /path\n"
        "[2026-03-11T00:13:22Z] Bash | npm run build | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    cursor_file.write_text("1")
    settings = {"permissions": {"allow": [], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    assert result["total_new_lines"] == 2
    assert result["cursor"] == 3
    patterns = {g["pattern"] for g in result["groups"]}
    assert "Bash(git add new.ts)" in patterns
    assert "Bash(npm run build)" in patterns
    assert "Bash(git add old.ts)" not in patterns  # was before cursor


def test_analyze_sorted_by_frequency(tmp_path):
    """Output groups are sorted by count descending."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | npm run build | CWD: /path\n"
        "[2026-03-11T00:13:21Z] Bash | git add foo.ts | CWD: /path\n"
        "[2026-03-11T00:13:22Z] Bash | git add bar.ts | CWD: /path\n"
        "[2026-03-11T00:13:23Z] Bash | git add baz.ts | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    settings = {"permissions": {"allow": [], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    assert len(result["groups"]) == 2
    assert result["groups"][0]["count"] >= result["groups"][1]["count"]
    assert result["groups"][0]["pattern"] == "Bash(git add *)"


def test_analyze_missing_permissions_key(tmp_path):
    """Settings dict without a permissions key should not crash."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | git add foo.ts | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings={},
        manual_path=manual_file,
    )

    assert len(result["groups"]) == 1


def test_analyze_filters_existing_rules(tmp_path):
    """Groups matching existing allow/deny rules are excluded."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | git add foo.ts | CWD: /path\n"
        "[2026-03-11T00:13:21Z] Bash | git add bar.ts | CWD: /path\n"
        "[2026-03-11T00:13:22Z] Bash | npm run build | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    settings = {"permissions": {"allow": ["Bash(git add *)"], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    patterns = {g["pattern"] for g in result["groups"]}
    assert "Bash(git add *)" not in patterns
    assert "Bash(npm run build)" in patterns


def test_analyze_filters_manual_review(tmp_path):
    """Groups matching manual-review entries are excluded."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "[2026-03-11T00:13:20Z] Bash | git push origin main | CWD: /path\n"
        "[2026-03-11T00:13:21Z] Bash | git push origin dev | CWD: /path\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    settings = {"permissions": {"allow": [], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"
    manual_file.write_text("Bash(git push *)\n")

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    assert result["groups"] == []


def test_analyze_no_log_file(tmp_path):
    """Missing log file returns empty results."""
    from analyze_permissions import analyze

    result = analyze(
        log_path=tmp_path / "nonexistent.log",
        cursor_path=tmp_path / "cursor.txt",
        settings={"permissions": {"allow": [], "deny": []}},
        manual_path=tmp_path / "manual-review-commands.txt",
    )

    assert result["groups"] == []
    assert result["total_new_lines"] == 0
    assert result["cursor"] == 0


def test_analyze_skips_malformed_lines(tmp_path):
    """Malformed lines are skipped, valid lines still processed."""
    from analyze_permissions import analyze

    log_file = tmp_path / "permission-requests.log"
    log_file.write_text(
        "this is garbage\n"
        "[2026-03-11T00:13:20Z] Bash | git add foo.ts | CWD: /path\n"
        "\n"
    )
    cursor_file = tmp_path / "cursor.txt"
    settings = {"permissions": {"allow": [], "deny": []}}
    manual_file = tmp_path / "manual-review-commands.txt"

    result = analyze(
        log_path=log_file,
        cursor_path=cursor_file,
        settings=settings,
        manual_path=manual_file,
    )

    assert len(result["groups"]) == 1
    assert result["cursor"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_analyze_permissions.py::test_analyze_full_pipeline -v`
Expected: FAIL — `ImportError: cannot import name 'analyze'`

- [ ] **Step 3: Implement analyze function and CLI main**

```python
# add to scripts/analyze_permissions.py
import json
from pathlib import Path

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

    entries = []
    for line in new_lines:
        parsed = parse_log_line(line)
        if parsed is None:
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
        settings = {}
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/test_analyze_permissions.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze_permissions.py tests/test_analyze_permissions.py
git commit -m "Add main entry point with cursor and file I/O for permissions auditor"
```

---

## Chunk 2: Hook Script, Skill Files, and Cleanup

### Task 5: Hook script

**Files:**
- Create: `scripts/log-permission-requests.sh`

- [ ] **Step 1: Create the hook script**

```bash
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/log-permission-requests.sh`

- [ ] **Step 3: Commit**

```bash
git add scripts/log-permission-requests.sh
git commit -m "Add permission request logging hook script"
```

---

### Task 6: Skill SKILL.md

**Files:**
- Create: `skills/permissions-auditor/SKILL.md`

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: permissions-auditor
description: Use when managing Claude Code permission rules, analyzing permission request logs, installing the permission logging hook, or triaging allow/deny patterns in settings.json. Use when the user wants to reduce permission prompts or audit which commands require approval.
---

# Permissions Auditor

Analyze permission request logs to find recurring patterns, then triage them into allow/deny rules or mark them for continued manual review.

## When to Use

- User wants to install the permission logging hook
- User wants to analyze which commands are triggering permission prompts
- User wants to add commands to their allow or deny list
- User wants to audit or manage their permission rules

## Sub-Tasks

| Task | Doc | When |
|------|-----|------|
| Install Hook | `docs/install.md` | Setting up permission logging for the first time |
| Analyze & Triage | `docs/analyze.md` | Reviewing logged permissions and adding rules |
```

- [ ] **Step 2: Commit**

```bash
git add skills/permissions-auditor/SKILL.md
git commit -m "Add permissions-auditor skill routing layer"
```

---

### Task 7: Skill docs/install.md

**Files:**
- Create: `skills/permissions-auditor/docs/install.md`

- [ ] **Step 1: Create install.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/permissions-auditor/docs/install.md
git commit -m "Add hook installation instructions for permissions auditor"
```

---

### Task 8: Skill docs/analyze.md

**Files:**
- Create: `skills/permissions-auditor/docs/analyze.md`

- [ ] **Step 1: Create analyze.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/permissions-auditor/docs/analyze.md
git commit -m "Add analysis and triage workflow for permissions auditor"
```

---

### Task 9: Remove old plugin infrastructure

**Files:**
- Delete: `plugins/log-permission-requests/log-permission-requests.sh`
- Delete: `plugins/log-permission-requests/plugin.json`
- Delete: `scripts/install_plugin.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Remove old plugin files and install_plugin.py**

```bash
rm plugins/log-permission-requests/log-permission-requests.sh
rm plugins/log-permission-requests/plugin.json
rmdir plugins/log-permission-requests
rmdir plugins
rm scripts/install_plugin.py
```

- [ ] **Step 2: Update CLAUDE.md**

Remove references to `install_plugin.py` and `plugins/` directory. In the Repository Structure section, replace `plugins/` references. In Common Commands, remove the plugin install commands.

The updated Repository Structure should be:

```
scripts/
  create_skill.py           # Generate a skill from a documentation URL
  install_skill.py          # Symlink skills into ~/.claude/skills/
  analyze_permissions.py    # Analyze permission request logs
  log-permission-requests.sh # Permission logging hook script
skills/
  <library>/
    SKILL.md                # Routing layer (loaded on invocation)
    docs/<topic>.md         # Detailed reference (read on demand)
tests/
  test_create_skill.py
  test_install_skill.py
  test_analyze_permissions.py
docs/plans/                 # Design and implementation documents
```

Remove the plugin commands section from Common Commands entirely.

- [ ] **Step 3: Run all tests to make sure nothing is broken**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (test_install_plugin.py does not exist, so no breakage)

- [ ] **Step 4: Commit**

```bash
git rm -r plugins/log-permission-requests/
git rm scripts/install_plugin.py
rmdir plugins 2>/dev/null || true
git add CLAUDE.md
git commit -m "Remove old plugin infrastructure, replaced by permissions-auditor skill"
```

---

### Task 10: Final integration test

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Verify script runs against real log (if present)**

Run: `python scripts/analyze_permissions.py`
Expected: JSON output to stdout (may show groups or empty if cursor is ahead)

- [ ] **Step 3: Verify skill files are well-formed**

Check that `skills/permissions-auditor/SKILL.md` has valid YAML frontmatter and the doc references exist:
- `skills/permissions-auditor/docs/install.md` exists
- `skills/permissions-auditor/docs/analyze.md` exists
