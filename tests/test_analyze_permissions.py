"""Tests for the permissions log analyzer."""

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
