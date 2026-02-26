import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "create_skill.py")

VALID_SKILL_DATA = {
    "library_description": "A lib.",
    "trigger_description": "Use when using lib",
    "when_to_use": ["Writing code"],
    "key_patterns": ["Pattern 1"],
    "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}],
}


def _make_openai_mock_client(response_text: str) -> MagicMock:
    """Build a mock OpenAI client that returns response_text from chat completions."""
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

def test_create_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "name" in result.stdout.lower()
    assert "url" in result.stdout.lower()


def test_build_skill_md():
    """Verify SKILL.md generation from structured data."""
    from create_skill import build_skill_md

    data = {
        "library_description": "A query builder for SQL databases.",
        "trigger_description": "Use when writing code that uses the knex query builder",
        "when_to_use": ["Writing SQL queries with knex", "Debugging knex errors"],
        "key_patterns": ["Always dispose connections", "Use transactions for multi-step ops"],
        "topics": [
            {
                "filename": "queries.md",
                "title": "Query Building",
                "description": "SELECT, INSERT, UPDATE, DELETE",
                "content": "# Queries\n..."
            }
        ]
    }

    result = build_skill_md("knex", data)

    assert "---" in result
    assert "name: knex" in result
    assert "Use when writing code that uses the knex query builder" in result
    assert "## When to Use" in result
    assert "## Reference" in result
    assert "## Key Patterns" in result
    assert "docs/queries.md" in result


def test_write_skill(tmp_path):
    """Verify file writing."""
    from create_skill import write_skill

    data = {
        "library_description": "A query builder.",
        "trigger_description": "Use when using knex",
        "when_to_use": ["Writing queries"],
        "key_patterns": ["Use transactions"],
        "topics": [
            {
                "filename": "queries.md",
                "title": "Queries",
                "description": "Query building",
                "content": "# Queries\n\nSELECT * FROM users"
            }
        ]
    }

    skill_dir = tmp_path / "knex"
    write_skill(skill_dir, data)

    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "docs" / "queries.md").exists()
    assert "name: knex" in (skill_dir / "SKILL.md").read_text()
    assert "SELECT * FROM users" in (skill_dir / "docs" / "queries.md").read_text()


def test_parse_skill_response_valid():
    """Verify parse_skill_response extracts valid JSON."""
    from create_skill import parse_skill_response

    result = parse_skill_response(json.dumps(VALID_SKILL_DATA))
    assert result["library_description"] == "A lib."


def test_parse_skill_response_with_code_fence():
    """Verify parse_skill_response strips markdown code fences."""
    from create_skill import parse_skill_response

    raw = f"```json\n{json.dumps(VALID_SKILL_DATA)}\n```"
    result = parse_skill_response(raw)
    assert result["library_description"] == "A lib."


def test_parse_skill_response_missing_keys():
    """Verify parse_skill_response exits on missing keys."""
    from create_skill import parse_skill_response
    with pytest.raises(SystemExit):
        parse_skill_response('{"library_description": "incomplete"}')


def test_parse_skill_response_invalid_json():
    """Verify parse_skill_response exits on invalid JSON."""
    from create_skill import parse_skill_response

    with pytest.raises(SystemExit):
        parse_skill_response("not json at all")


def test_cli_backend_success():
    """Verify CliBackend parses claude CLI JSON output."""
    from create_skill import CliBackend

    inner_json = json.dumps(VALID_SKILL_DATA)
    claude_output = json.dumps({"result": inner_json, "session_id": "test", "usage": {}})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=claude_output,
            stderr=""
        )
        result = CliBackend().generate("sonnet", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args
    assert "-p" in call_args


def test_create_skill_help_shows_backend():
    """Verify --help shows the backend options including openai."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "backend" in result.stdout.lower()
    assert "openai" in result.stdout.lower()


def test_cli_backend_not_found():
    """Verify CliBackend exits when claude is not installed."""
    from create_skill import CliBackend

    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit):
            CliBackend().generate("sonnet", "testlib", "doc content")


def test_backend_is_abstract():
    """Verify Backend cannot be instantiated directly."""
    from create_skill import Backend

    with pytest.raises(TypeError):
        Backend()


def test_openai_backend_success():
    """Verify OpenAIBackend calls OpenAI API and parses response."""
    from create_skill import OpenAIBackend

    mock_client = _make_openai_mock_client(json.dumps(VALID_SKILL_DATA))

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI", return_value=mock_client):
            result = OpenAIBackend().generate("gpt-5.2", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-5.2"
    assert call_kwargs["max_completion_tokens"] == 16000


def test_openai_backend_missing_api_key():
    """Verify OpenAIBackend exits when no API key is available."""
    from create_skill import OpenAIBackend

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit):
            OpenAIBackend().generate("gpt-5.2", "testlib", "doc content")


def test_openai_backend_api_key_override():
    """Verify OpenAIBackend accepts api_key constructor arg over env var."""
    from create_skill import OpenAIBackend

    mock_client = _make_openai_mock_client(json.dumps(VALID_SKILL_DATA))

    with patch.dict("os.environ", {}, clear=True):
        with patch("openai.OpenAI", return_value=mock_client) as mock_openai_cls:
            result = OpenAIBackend(api_key="flag-key").generate("gpt-5.2", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_openai_cls.assert_called_once_with(api_key="flag-key")
