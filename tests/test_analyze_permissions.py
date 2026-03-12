"""Tests for the permissions log analyzer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_permissions import (
    parse_log_line,
    split_compound_command,
    group_commands,
    filter_groups,
)


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


def test_split_simple_command():
    """A single command returns as-is."""
    assert split_compound_command("git add foo.ts") == ["git add foo.ts"]


def test_split_and_operator():
    """Commands joined by && are split."""
    result = split_compound_command("git add foo.ts && git commit -m 'fix'")
    assert result == ["git add foo.ts", "git commit -m 'fix'"]


def test_split_or_operator():
    """Commands joined by || are split."""
    result = split_compound_command("git rm old.ts || true")
    assert result == ["git rm old.ts", "true"]


def test_split_semicolon():
    """Commands joined by ; are split."""
    result = split_compound_command("echo hello; echo world")
    assert result == ["echo hello", "echo world"]


def test_split_pipe():
    """Commands joined by | are split."""
    result = split_compound_command("cat file.txt | grep pattern")
    assert result == ["cat file.txt", "grep pattern"]


def test_split_mixed_operators():
    """Multiple different operators in one command."""
    result = split_compound_command("git add . && git status | grep modified")
    assert result == ["git add .", "git status", "grep modified"]


def test_split_strips_whitespace():
    """Sub-commands are trimmed."""
    result = split_compound_command("  git add foo.ts  &&  git commit -m 'fix'  ")
    assert result == ["git add foo.ts", "git commit -m 'fix'"]


def test_split_skips_empty_subcommands():
    """Empty sub-commands from leading/trailing operators are skipped."""
    result = split_compound_command("&& git add foo.ts &&")
    assert result == ["git add foo.ts"]


def test_split_comment_lines_skipped():
    """Lines starting with # after splitting are filtered out."""
    result = split_compound_command("# this is a comment\ngit add foo.ts")
    assert "git add foo.ts" in result
    assert not any(r.startswith("#") for r in result)


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


def test_group_splits_compound_commands():
    """Compound commands are split before grouping."""
    entries = [
        ("Bash", "git add foo.ts && git commit -m 'fix'"),
        ("Bash", "git add bar.ts && git status"),
    ]
    groups = group_commands(entries)
    patterns = {g["pattern"] for g in groups}
    assert "Bash(git add *)" in patterns
    assert "Bash(git commit -m 'fix')" in patterns  # singleton
    assert "Bash(git status)" in patterns  # singleton


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
