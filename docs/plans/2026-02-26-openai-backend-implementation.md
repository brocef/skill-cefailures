# OpenAI Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor skill generation backends into a Backend ABC and add OpenAI SDK support.

**Architecture:** Extract existing `generate_skill_cli()` and `generate_skill_sdk()` into `CliBackend` and `AnthropicBackend` subclasses of an abstract `Backend` base class. Add `OpenAIBackend` as third implementation. Shared prompt building and response parsing stay as module-level functions. Backend-specific default models via `DEFAULT_MODELS` dict.

**Tech Stack:** Python 3, openai SDK (>=1.0.0), pytest, unittest.mock

**Design doc:** `docs/plans/2026-02-26-openai-backend-design.md`

---

### Task 1: Refactor existing backends into Backend ABC

**Files:**
- Modify: `scripts/create_skill.py:102-179`
- Test: `tests/test_create_skill.py`

**Step 1: Write the failing test for Backend ABC interface**

Add to `tests/test_create_skill.py`:

```python
def test_backend_is_abstract():
    """Verify Backend cannot be instantiated directly."""
    from create_skill import Backend
    import pytest

    with pytest.raises(TypeError):
        Backend()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py::test_backend_is_abstract -v`
Expected: FAIL with "ImportError" (Backend doesn't exist yet)

**Step 3: Write the Backend ABC and refactor CliBackend**

In `scripts/create_skill.py`, add `from abc import ABC, abstractmethod` to imports, then replace lines 102-151 with:

```python
DEFAULT_MODELS = {
    "cli": "claude-sonnet-4-6",
    "sdk": "claude-sonnet-4-6",
    "openai": "gpt-5.2",
}


class Backend(ABC):
    """Abstract base for skill generation backends."""

    @abstractmethod
    def generate(self, model: str, name: str, content: str) -> dict:
        """Analyze docs and return structured skill data dict."""

    def _build_prompt(self, name: str, content: str) -> str:
        return ANALYSIS_PROMPT.format(name=name, content=content)


class CliBackend(Backend):
    """Call claude CLI subprocess."""

    def generate(self, model: str, name: str, content: str) -> dict:
        prompt = self._build_prompt(name, content)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        try:
            result = subprocess.run(
                ["claude", "-p", "-", "--model", model, "--output-format", "json"],
                input=prompt,
                capture_output=True,
                text=True,
                env=env,
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

        try:
            claude_output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(
                f"Error: Failed to parse claude CLI output: {e}\n"
                f"Raw output (first 500 chars):\n{result.stdout[:500]}",
                file=sys.stderr,
            )
            sys.exit(1)

        if "result" not in claude_output:
            print(
                "Error: claude CLI output missing 'result' key.\n"
                f"Keys found: {list(claude_output.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

        return parse_skill_response(claude_output["result"])
```

**Step 4: Refactor AnthropicBackend**

Replace lines 153-179 (the old `generate_skill_sdk` function) with:

```python
class AnthropicBackend(Backend):
    """Call Anthropic SDK directly."""

    def generate(self, model: str, name: str, content: str) -> dict:
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
        prompt = self._build_prompt(name, content)

        response = client.messages.create(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        return parse_skill_response(response_text)
```

**Step 5: Update main() to use Backend classes**

In `main()`, replace the backend dispatch (lines 270-273) with:

```python
    backends = {
        "cli": CliBackend,
        "sdk": AnthropicBackend,
        "openai": OpenAIBackend,
    }

    # Resolve model default per backend
    model = args.model or DEFAULT_MODELS[args.backend]

    print(f"Generating skill with {model} ({args.backend} backend)...")
    backend = backends[args.backend]()
    skill_content = backend.generate(model, args.name, content)
```

Also update the argparser: change `--model` default to `None`:

```python
    parser.add_argument("--model", default=None, help=f"Model to use (default depends on backend)")
```

And expand `--backend` choices:

```python
    parser.add_argument(
        "--backend",
        choices=["cli", "sdk", "openai"],
        default="cli",
        help="LLM backend: 'cli' uses claude CLI (default), 'sdk' uses Anthropic API, 'openai' uses OpenAI API",
    )
```

Remove the old `DEFAULT_MODEL` constant at line 17.

**Step 6: Run all existing tests to verify refactor didn't break anything**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py -v`
Expected: All existing tests FAIL — they import old function names (`generate_skill_cli`). That's expected; we fix them in step 7.

**Step 7: Update existing tests for new class interface**

Replace `test_generate_skill_cli_success` with:

```python
def test_cli_backend_success():
    """Verify CliBackend parses claude CLI JSON output."""
    from create_skill import CliBackend

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
        result = CliBackend().generate("sonnet", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "claude" in call_args
    assert "-p" in call_args
```

Replace `test_generate_skill_cli_not_found` with:

```python
def test_cli_backend_not_found():
    """Verify CliBackend exits when claude is not installed."""
    from create_skill import CliBackend
    import pytest

    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit):
            CliBackend().generate("sonnet", "testlib", "doc content")
```

Update `test_create_skill_help_shows_backend` to also check for "openai":

```python
def test_create_skill_help_shows_backend():
    """Verify --help shows the backend options including openai."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "backend" in result.stdout.lower()
    assert "openai" in result.stdout.lower()
```

**Step 8: Run tests to verify refactor passes**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py -v`
Expected: All tests PASS (the new ABC test + updated existing tests).
Note: `test_create_skill_help_shows_backend` will fail because `OpenAIBackend` doesn't exist yet. That's fine — it gets added in Task 2.

**Step 9: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "refactor: extract Backend ABC from generate_skill functions"
```

---

### Task 2: Add OpenAI backend

**Files:**
- Modify: `scripts/create_skill.py` (add `OpenAIBackend` class)
- Modify: `tests/test_create_skill.py` (add OpenAI tests)
- Modify: `requirements.txt`

**Step 1: Write the failing test for OpenAI backend**

Add to `tests/test_create_skill.py`:

```python
def test_openai_backend_success():
    """Verify OpenAIBackend calls OpenAI API and parses response."""
    from create_skill import OpenAIBackend

    inner_json = json.dumps({
        "library_description": "A lib.",
        "trigger_description": "Use when using lib",
        "when_to_use": ["Writing code"],
        "key_patterns": ["Pattern 1"],
        "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}]
    })

    mock_message = MagicMock()
    mock_message.content = inner_json
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI", return_value=mock_client):
            result = OpenAIBackend().generate("gpt-5.2", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-5.2"
    assert call_kwargs["max_tokens"] == 16000
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py::test_openai_backend_success -v`
Expected: FAIL with "ImportError" (OpenAIBackend doesn't exist yet)

**Step 3: Write the failing test for missing API key**

Add to `tests/test_create_skill.py`:

```python
def test_openai_backend_missing_api_key():
    """Verify OpenAIBackend exits when no API key is available."""
    from create_skill import OpenAIBackend
    import pytest

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit):
            OpenAIBackend().generate("gpt-5.2", "testlib", "doc content")
```

**Step 4: Write the failing test for --api-key flag override**

Add to `tests/test_create_skill.py`:

```python
def test_openai_backend_api_key_override():
    """Verify OpenAIBackend accepts api_key constructor arg over env var."""
    from create_skill import OpenAIBackend

    inner_json = json.dumps({
        "library_description": "A lib.",
        "trigger_description": "Use when using lib",
        "when_to_use": ["Writing code"],
        "key_patterns": ["Pattern 1"],
        "topics": [{"filename": "a.md", "title": "A", "description": "A desc", "content": "# A"}]
    })

    mock_message = MagicMock()
    mock_message.content = inner_json
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.dict("os.environ", {}, clear=True):
        with patch("openai.OpenAI", return_value=mock_client) as mock_openai_cls:
            result = OpenAIBackend(api_key="flag-key").generate("gpt-5.2", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_openai_cls.assert_called_once_with(api_key="flag-key")
```

**Step 5: Implement OpenAIBackend**

Add to `scripts/create_skill.py`, after `AnthropicBackend`:

```python
class OpenAIBackend(Backend):
    """Call OpenAI SDK."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key

    def generate(self, model: str, name: str, content: str) -> dict:
        try:
            import openai
        except ImportError:
            print(
                "Error: openai package not installed. Run: pip install openai\n"
                "Or use --backend cli (default) which requires no extra packages.",
                file=sys.stderr,
            )
            sys.exit(1)

        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print(
                "Error: OpenAI API key not found. Set OPENAI_API_KEY environment variable\n"
                "or pass --api-key flag.",
                file=sys.stderr,
            )
            sys.exit(1)

        client = openai.OpenAI(api_key=api_key)
        prompt = self._build_prompt(name, content)

        response = client.chat.completions.create(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.choices[0].message.content
        return parse_skill_response(response_text)
```

**Step 6: Update main() for --api-key flag and OpenAI backend construction**

Add the `--api-key` argument to the argparser:

```python
    parser.add_argument("--api-key", default=None, help="API key (used by openai backend, overrides env var)")
```

Update the backend dispatch to pass `api_key`:

```python
    if args.backend == "openai":
        backend = OpenAIBackend(api_key=args.api_key)
    else:
        backend = backends[args.backend]()
```

**Step 7: Run all tests**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py -v`
Expected: ALL PASS

**Step 8: Update requirements.txt**

Append to `requirements.txt`:

```
# Optional: only needed with --backend openai
# openai>=1.0.0
```

**Step 9: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py requirements.txt
git commit -m "feat: add OpenAI backend with --api-key support"
```

---

### Task 3: Verify end-to-end with help output

**Step 1: Run the script with --help to verify all options appear**

Run: `cd /Users/brian/Projects/skill-cefailures && python scripts/create_skill.py --help`
Expected: Output shows `--backend {cli,sdk,openai}`, `--api-key`, and `--model` with no default shown.

**Step 2: Run full test suite one final time**

Run: `cd /Users/brian/Projects/skill-cefailures && python -m pytest tests/test_create_skill.py -v`
Expected: ALL PASS

**Step 3: Commit any remaining changes (if needed)**

Only if there were fixes needed from steps 1-2.
