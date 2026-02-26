# Dual Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Claude CLI backend to `create_skill.py` as the default, keeping Anthropic SDK as an option via `--backend sdk`.

**Architecture:** Extract JSON parsing/validation into a shared `parse_skill_response()` helper. Add `generate_skill_cli()` that calls `claude -p` via subprocess. Rename current `generate_skill()` to `generate_skill_sdk()` with lazy `import anthropic`. Add `--backend {cli,sdk}` flag defaulting to `cli`. Update `main()` to dispatch.

**Tech Stack:** Python 3, subprocess, httpx. Optional: anthropic SDK.

---

### Task 1: Extract parse_skill_response helper

Extract the JSON parsing and validation logic from the current `generate_skill()` into a standalone function so both backends can share it.

**Files:**
- Modify: `scripts/create_skill.py:62-108`
- Modify: `tests/test_create_skill.py`

**Step 1: Write the failing test**

Add to `tests/test_create_skill.py`:

```python
def test_parse_skill_response_valid():
    """Verify parse_skill_response extracts valid JSON."""
    from create_skill import parse_skill_response

    raw = json.dumps({
        "library_description": "A lib.",
        "trigger_description": "Use when using lib",
        "when_to_use": ["Writing code"],
        "key_patterns": ["Pattern 1"],
        "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}]
    })
    result = parse_skill_response(raw)
    assert result["library_description"] == "A lib."


def test_parse_skill_response_with_code_fence():
    """Verify parse_skill_response strips markdown code fences."""
    from create_skill import parse_skill_response

    inner = json.dumps({
        "library_description": "A lib.",
        "trigger_description": "Use when using lib",
        "when_to_use": ["Writing code"],
        "key_patterns": ["Pattern 1"],
        "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}]
    })
    raw = f"```json\n{inner}\n```"
    result = parse_skill_response(raw)
    assert result["library_description"] == "A lib."


def test_parse_skill_response_missing_keys():
    """Verify parse_skill_response exits on missing keys."""
    from create_skill import parse_skill_response
    import pytest

    with pytest.raises(SystemExit):
        parse_skill_response('{"library_description": "incomplete"}')


def test_parse_skill_response_invalid_json():
    """Verify parse_skill_response exits on invalid JSON."""
    from create_skill import parse_skill_response
    import pytest

    with pytest.raises(SystemExit):
        parse_skill_response("not json at all")
```

Note: add `import json` at the top of the test file since `test_parse_skill_response_with_code_fence` uses `json.dumps`.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_create_skill.py::test_parse_skill_response_valid -v`
Expected: FAIL — `parse_skill_response` doesn't exist yet

**Step 3: Implement parse_skill_response**

In `scripts/create_skill.py`, add this function after `ANALYSIS_PROMPT` (before the current `generate_skill`):

```python
def parse_skill_response(response_text: str) -> dict:
    """Parse LLM response text into validated skill data dict.

    Strips markdown code fences, parses JSON, validates required keys.
    Calls sys.exit(1) on failure with a user-friendly error message.
    """
    # Strip markdown code fences
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        skill_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(
            f"Error: Failed to parse LLM response as JSON: {e}\n"
            f"Raw response (first 500 chars):\n{response_text[:500]}",
            file=sys.stderr,
        )
        sys.exit(1)

    required_keys = [
        "library_description",
        "trigger_description",
        "when_to_use",
        "key_patterns",
        "topics",
    ]
    missing = [k for k in required_keys if k not in skill_data]
    if missing:
        print(
            f"Error: LLM response is missing required keys: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return skill_data
```

Then update the current `generate_skill` to use it — replace lines 75-108 with:

```python
    response_text = response.content[0].text
    return parse_skill_response(response_text)
```

**Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (8 tests — 4 existing + 4 new)

**Step 5: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "refactor: extract parse_skill_response shared helper"
```

---

### Task 2: Add generate_skill_cli function

Add the CLI backend that calls `claude -p` via subprocess.

**Files:**
- Modify: `scripts/create_skill.py`
- Modify: `tests/test_create_skill.py`

**Step 1: Write the failing test**

Add to `tests/test_create_skill.py`:

```python
from unittest.mock import patch, MagicMock

def test_generate_skill_cli_success():
    """Verify generate_skill_cli parses claude CLI JSON output."""
    from create_skill import generate_skill_cli

    inner_json = json.dumps({
        "library_description": "A lib.",
        "trigger_description": "Use when using lib",
        "when_to_use": ["Writing code"],
        "key_patterns": ["Pattern 1"],
        "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}]
    })
    claude_output = json.dumps({"result": inner_json, "session_id": "test", "usage": {}})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=claude_output,
            stderr=""
        )
        result = generate_skill_cli("sonnet", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args
    assert "-p" in call_args


def test_generate_skill_cli_not_found():
    """Verify generate_skill_cli exits when claude is not installed."""
    from create_skill import generate_skill_cli
    import pytest

    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit):
            generate_skill_cli("sonnet", "testlib", "doc content")
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_create_skill.py::test_generate_skill_cli_success -v`
Expected: FAIL — `generate_skill_cli` doesn't exist yet

**Step 3: Implement generate_skill_cli**

Add to `scripts/create_skill.py`, after `parse_skill_response` and before the current `generate_skill`:

```python
import subprocess


def generate_skill_cli(model: str, name: str, content: str) -> dict:
    """Call claude CLI to analyze docs and generate structured skill content."""
    prompt = ANALYSIS_PROMPT.format(name=name, content=content)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--output-format", "json"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(
            "Error: claude CLI not found. Install Claude Code or use --backend sdk.",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode != 0:
        print(
            f"Error: claude CLI exited with code {result.returncode}\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)

    # claude --output-format json returns {"result": "...", ...}
    try:
        claude_output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(
            f"Error: Failed to parse claude CLI output: {e}\n"
            f"Raw output (first 500 chars):\n{result.stdout[:500]}",
            file=sys.stderr,
        )
        sys.exit(1)

    response_text = claude_output["result"]
    return parse_skill_response(response_text)
```

Note: `import subprocess` is already in stdlib. Add it to the top-level imports alongside the other stdlib imports.

**Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (10 tests)

**Step 5: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "feat: add generate_skill_cli using claude -p"
```

---

### Task 3: Rename generate_skill to generate_skill_sdk with lazy import

Rename the current SDK-based function and make the `anthropic` import lazy.

**Files:**
- Modify: `scripts/create_skill.py:11` (remove top-level `import anthropic`)
- Modify: `scripts/create_skill.py` (rename function, add lazy import + API key check inside it)

**Step 1: Rename and restructure**

In `scripts/create_skill.py`:

1. Remove `import anthropic` from line 11 (top-level imports).

2. Rename `generate_skill` to `generate_skill_sdk` and restructure it:

```python
def generate_skill_sdk(model: str, name: str, content: str) -> dict:
    """Call Anthropic SDK to analyze docs and generate structured skill content."""
    try:
        import anthropic
    except ImportError:
        print(
            "Error: anthropic package not installed. Run: pip install anthropic\n"
            "Or use --backend cli (default) which requires no extra packages.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    prompt = ANALYSIS_PROMPT.format(name=name, content=content)

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    return parse_skill_response(response_text)
```

Note: the function signature changes — it no longer takes a `client` parameter. The client is created internally after the lazy import and API key check.

**Step 2: Verify the help test still passes**

The `test_create_skill_help` test runs the script with `--help`. Since `import anthropic` is no longer top-level, `--help` will work even without the anthropic package installed (httpx is still required).

Run: `python -m pytest tests/test_create_skill.py::test_create_skill_help -v`
Expected: PASS

**Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add scripts/create_skill.py
git commit -m "refactor: rename generate_skill to generate_skill_sdk with lazy import"
```

---

### Task 4: Add --backend flag and update main()

Wire up the `--backend` flag and dispatch to the correct function.

**Files:**
- Modify: `scripts/create_skill.py` (main function)
- Modify: `tests/test_create_skill.py`

**Step 1: Write the failing test**

Add to `tests/test_create_skill.py`:

```python
def test_create_skill_help_shows_backend():
    """Verify --help shows the backend option."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "backend" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_create_skill.py::test_create_skill_help_shows_backend -v`
Expected: FAIL — "backend" not in help output yet

**Step 3: Update main()**

In `scripts/create_skill.py`, modify `main()`:

1. Add the `--backend` argument after the existing args:

```python
    parser.add_argument(
        "--backend",
        choices=["cli", "sdk"],
        default="cli",
        help="LLM backend: 'cli' uses claude CLI (default), 'sdk' uses Anthropic API",
    )
```

2. Replace the entire block from `# Check for API key` through `skill_content = generate_skill(...)` with:

```python
    # Generate the skill
    print(f"Generating skill with {args.model} ({args.backend} backend)...")
    if args.backend == "cli":
        skill_content = generate_skill_cli(args.model, args.name, content)
    else:
        skill_content = generate_skill_sdk(args.model, args.name, content)
```

This removes the API key check and client creation from `main()` since those are now inside `generate_skill_sdk()`.

**Step 4: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS (11 tests)

**Step 5: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "feat: add --backend flag to choose between cli and sdk"
```

---

### Task 5: Update requirements.txt and README.md

Update docs to reflect that `anthropic` is now optional and CLI is the default.

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`

**Step 1: Update requirements.txt**

```
httpx>=0.27.0
# Optional: only needed with --backend sdk
# anthropic>=0.42.0
```

Move `anthropic` to a comment since it's no longer required for the default workflow.

**Step 2: Update README.md**

Replace the "Create a new skill" section with:

```markdown
### Create a new skill

```bash
# Using Claude CLI (default — no API key needed)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md"

# Using Anthropic SDK (requires ANTHROPIC_API_KEY)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md" --backend sdk
```

This fetches the documentation, uses Claude to analyze and split it into a SKILL.md routing layer plus topical reference docs, and writes everything to `skills/<name>/`.

By default, uses the `claude` CLI (requires [Claude Code](https://claude.com/claude-code)). Use `--backend sdk` for the Anthropic API directly (requires `pip install anthropic` and `ANTHROPIC_API_KEY`).
```

**Step 3: Commit**

```bash
git add requirements.txt README.md
git commit -m "docs: update requirements and README for dual backend support"
```
