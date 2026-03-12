"""Tests for the permissions log analyzer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze_permissions import parse_log_line, split_compound_command


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
