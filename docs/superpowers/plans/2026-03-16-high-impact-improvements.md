# High-Impact Improvements Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix backend default documentation bug, add HTML-to-markdown extraction in `fetch_document()`, and fill test coverage gaps across three scripts.

**Architecture:** Three independent changes: (1) text-only fixes to argparse help and CLAUDE.md, (2) `html2text` integration in `fetch_document()` with content-type detection, (3) comprehensive test suites using `tmp_path` + monkeypatched path constants for filesystem isolation.

**Tech Stack:** Python 3, pytest, html2text, httpx, unittest.mock

**Spec:** `docs/superpowers/specs/2026-03-16-high-impact-improvements-design.md`

---

## Chunk 1: Backend Default Fix + HTML Extraction

### Task 1: Fix backend default documentation

**Files:**
- Modify: `scripts/create_skill.py:204,238,326-331`
- Modify: `CLAUDE.md:18-55`

- [ ] **Step 1: Fix argparse help string**

In `scripts/create_skill.py`, change the `--backend` help text (line 331):

```python
# Before:
        help="LLM backend: 'cli' uses claude CLI (default), 'sdk' uses Anthropic API, 'openai' uses OpenAI API",

# After:
        help="LLM backend: 'cli' uses claude CLI, 'sdk' uses Anthropic API, 'openai' uses OpenAI API (default)",
```

- [ ] **Step 2: Fix stale error messages in AnthropicBackend and OpenAIBackend**

In `scripts/create_skill.py`, update both ImportError messages (lines 204 and 238):

```python
# Before (line 204, AnthropicBackend):
                "Or use --backend cli (default) which requires no extra packages.",

# After:
                "Or use --backend cli which requires no extra packages.",

# Before (line 238, OpenAIBackend):
                "Or use --backend cli (default) which requires no extra packages.",

# After:
                "Or use --backend cli which requires no extra packages.",
```

- [ ] **Step 3: Update CLAUDE.md**

Update the Common Commands section to reflect `openai` as default:

```markdown
# Before:
# Create a new skill (default: claude CLI backend)
python scripts/create_skill.py --name <lib> --url "<docs-url>"

# After:
# Create a new skill (default: openai backend)
python scripts/create_skill.py --name <lib> --url "<docs-url>"
```

Update the Tech Stack section to include `html2text`:

```markdown
# Before:
- **Dependencies:** `httpx` (required), `anthropic` and `openai` (optional, per backend)

# After:
- **Dependencies:** `httpx` and `html2text` (required), `anthropic` and `openai` (optional, per backend)
```

Update Repository Structure to include `install_plugin.py`, `plugins/`, and `test_install_plugin.py`:

```markdown
scripts/
  create_skill.py     # Generate a skill from a documentation URL
  install_skill.py    # Symlink skills into ~/.claude/skills/
  install_plugin.py   # Symlink plugins into ~/.claude/hooks/
skills/
  <library>/
    SKILL.md           # Routing layer (loaded on invocation)
    docs/<topic>.md    # Detailed reference (read on demand)
plugins/
  <plugin>/
    plugin.json        # Plugin metadata and hook definitions
    *.sh               # Hook scripts
tests/
  test_create_skill.py
  test_install_skill.py
  test_install_plugin.py
docs/plans/            # Design and implementation documents
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `python -m pytest tests/ -v`
Expected: All existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/create_skill.py CLAUDE.md
git commit -m "Fixed backend default documentation to reflect openai as default"
```

---

### Task 2: Add HTML content extraction to fetch_document

**Files:**
- Modify: `requirements.txt`
- Modify: `scripts/create_skill.py:19-23`
- Modify: `tests/test_create_skill.py`

- [ ] **Step 1: Add html2text dependency**

Add to `requirements.txt` after the `httpx` line:

```
html2text>=2024.2.26
```

Run: `pip install -r requirements.txt`

- [ ] **Step 2: Write failing tests for HTML conversion and passthrough**

Add to `tests/test_create_skill.py`:

```python
def test_fetch_document_html_conversion():
    """Verify fetch_document converts HTML responses to markdown."""
    from create_skill import fetch_document

    html_content = "<html><body><h1>Hello</h1><p>World</p></body></html>"
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response):
        result = fetch_document("http://example.com")

    # Should contain markdown heading, not raw HTML tags
    assert "<h1>" not in result
    assert "Hello" in result


def test_fetch_document_plain_text_passthrough():
    """Verify fetch_document returns plain text unchanged."""
    from create_skill import fetch_document

    plain_content = "# Hello\n\nThis is markdown already."
    mock_response = MagicMock()
    mock_response.text = plain_content
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response):
        result = fetch_document("http://example.com")

    assert result == plain_content
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_create_skill.py::test_fetch_document_html_conversion tests/test_create_skill.py::test_fetch_document_plain_text_passthrough -v`
Expected: FAIL — `fetch_document` doesn't accept mock responses / current implementation doesn't convert HTML.

- [ ] **Step 4: Implement HTML conversion in fetch_document**

Update `scripts/create_skill.py`. Add `import html2text` at the top (after `import httpx`), then modify `fetch_document`:

```python
import html2text

# ...

def fetch_document(url: str) -> str:
    """Download text content from a URL, converting HTML to markdown if needed."""
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/html"):
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.body_width = 0
        return converter.handle(response.text)
    return response.text
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_create_skill.py::test_fetch_document_html_conversion tests/test_create_skill.py::test_fetch_document_plain_text_passthrough -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt scripts/create_skill.py tests/test_create_skill.py
git commit -m "Added HTML-to-markdown conversion in fetch_document via html2text"
```

---

### Task 3: Add AnthropicBackend tests

**Files:**
- Modify: `tests/test_create_skill.py`

- [ ] **Step 1: Write AnthropicBackend test helpers and tests**

Add to `tests/test_create_skill.py`:

```python
def _make_anthropic_mock_client(response_text: str) -> MagicMock:
    """Build a mock Anthropic client that returns response_text from messages.create."""
    mock_content_block = MagicMock()
    mock_content_block.text = response_text
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def test_anthropic_backend_success():
    """Verify AnthropicBackend calls Anthropic API and parses response."""
    from create_skill import AnthropicBackend

    mock_client = _make_anthropic_mock_client(json.dumps(VALID_SKILL_DATA))
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = AnthropicBackend().generate("claude-sonnet-4-6", "testlib", "doc content")

    assert result["library_description"] == "A lib."
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 16000


def test_anthropic_backend_missing_api_key():
    """Verify AnthropicBackend exits when ANTHROPIC_API_KEY is not set."""
    from create_skill import AnthropicBackend

    mock_anthropic = MagicMock()

    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit):
                AnthropicBackend().generate("claude-sonnet-4-6", "testlib", "doc content")
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_create_skill.py::test_anthropic_backend_success tests/test_create_skill.py::test_anthropic_backend_missing_api_key -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_create_skill.py
git commit -m "Added AnthropicBackend test coverage"
```

---

## Chunk 2: install_skill.py Test Coverage

### Task 4: Add comprehensive tests for install_skill.py

**Files:**
- Modify: `tests/test_install_skill.py`

All tests use `monkeypatch.setattr` to redirect `install_skill.SKILLS_DIR` and `install_skill.TARGET_DIR` to subdirs of `tmp_path`.

- [ ] **Step 1: Write test scaffold and helper fixture**

Replace the contents of `tests/test_install_skill.py` (keeping the existing help test):

```python
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "install_skill.py")

import install_skill


@pytest.fixture
def skill_dirs(tmp_path, monkeypatch):
    """Set up isolated skills and target directories."""
    skills_dir = tmp_path / "skills"
    target_dir = tmp_path / "target"
    skills_dir.mkdir()
    target_dir.mkdir()
    monkeypatch.setattr(install_skill, "SKILLS_DIR", skills_dir)
    monkeypatch.setattr(install_skill, "TARGET_DIR", target_dir)
    return skills_dir, target_dir


def _create_skill(skills_dir: Path, name: str) -> Path:
    """Create a minimal skill directory with SKILL.md."""
    skill_dir = skills_dir / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"# {name}")
    return skill_dir


def test_install_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()
```

- [ ] **Step 2: Write get_available_skills test**

```python
def test_get_available_skills(skill_dirs):
    """Verify get_available_skills filters directories without SKILL.md."""
    skills_dir, _ = skill_dirs
    _create_skill(skills_dir, "valid-skill")
    # Directory without SKILL.md should be excluded
    (skills_dir / "no-skill-md").mkdir()
    # .gitkeep file should be excluded (not a directory)
    (skills_dir / ".gitkeep").touch()

    result = install_skill.get_available_skills()
    assert result == ["valid-skill"]
```

- [ ] **Step 3: Write install/remove symlink tests**

```python
def test_install_skill_creates_symlink(skill_dirs):
    """Verify install_skill creates a symlink in the target directory."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    install_skill.install_skill("mylib")

    target = target_dir / "mylib"
    assert target.is_symlink()
    assert target.resolve() == (skills_dir / "mylib").resolve()


def test_install_skill_force_overwrites(skill_dirs):
    """Verify --force replaces an existing symlink."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create an existing symlink pointing somewhere else
    target = target_dir / "mylib"
    target.symlink_to("/tmp")

    install_skill.install_skill("mylib", force=True)

    assert target.is_symlink()
    assert target.resolve() == (skills_dir / "mylib").resolve()


def test_install_skill_conflict_without_force(skill_dirs, capsys):
    """Verify warning when target exists without --force."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create an existing symlink
    target = target_dir / "mylib"
    target.symlink_to("/tmp")

    install_skill.install_skill("mylib", force=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_install_skill_real_dir_exits(skill_dirs):
    """Verify sys.exit when target is a real directory."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Create a real directory at the target
    (target_dir / "mylib").mkdir()

    with pytest.raises(SystemExit):
        install_skill.install_skill("mylib", force=True)


def test_install_skill_missing_skill_md(skill_dirs):
    """Verify sys.exit for a skill directory without SKILL.md."""
    skills_dir, _ = skill_dirs
    (skills_dir / "bad-skill").mkdir()

    with pytest.raises(SystemExit):
        install_skill.install_skill("bad-skill")


def test_remove_skill(skill_dirs):
    """Verify remove_skill removes the symlink."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "mylib")

    # Install first, then remove
    install_skill.install_skill("mylib")
    assert (target_dir / "mylib").is_symlink()

    install_skill.remove_skill("mylib")
    assert not (target_dir / "mylib").exists()


def test_remove_skill_not_symlink(skill_dirs, capsys):
    """Verify warning when target is not a symlink."""
    install_skill.remove_skill("nonexistent")

    captured = capsys.readouterr()
    assert "not a symlink" in captured.err
```

- [ ] **Step 4: Write --list and --all tests**

```python
def test_list_skills(skill_dirs, capsys, monkeypatch):
    """Verify --list shows available skills with install status."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "installed-lib")
    _create_skill(skills_dir, "uninstalled-lib")

    install_skill.install_skill("installed-lib")

    monkeypatch.setattr("sys.argv", ["install_skill.py", "--list"])
    install_skill.main()

    captured = capsys.readouterr()
    assert "[✓] installed-lib" in captured.out
    assert "[ ] uninstalled-lib" in captured.out


def test_install_all(skill_dirs, monkeypatch):
    """Verify --all installs every available skill."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "lib-a")
    _create_skill(skills_dir, "lib-b")

    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all"])
    install_skill.main()

    assert (target_dir / "lib-a").is_symlink()
    assert (target_dir / "lib-b").is_symlink()


def test_remove_all(skill_dirs, monkeypatch):
    """Verify --all --remove removes every installed skill."""
    skills_dir, target_dir = skill_dirs
    _create_skill(skills_dir, "lib-a")
    _create_skill(skills_dir, "lib-b")

    # Install all first
    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all"])
    install_skill.main()

    # Remove all
    monkeypatch.setattr("sys.argv", ["install_skill.py", "--all", "--remove"])
    install_skill.main()

    assert not (target_dir / "lib-a").exists()
    assert not (target_dir / "lib-b").exists()
```

- [ ] **Step 5: Run all install_skill tests**

Run: `python -m pytest tests/test_install_skill.py -v`
Expected: All tests pass.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_install_skill.py
git commit -m "Added comprehensive test coverage for install_skill.py"
```

---

## Chunk 3: install_plugin.py Test Coverage

### Task 5: Fix load_plugin_config error handling

**Files:**
- Modify: `scripts/install_plugin.py:30-36`

- [ ] **Step 1: Write failing test for malformed plugin.json**

Create `tests/test_install_plugin.py` with initial scaffolding and this test:

```python
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "install_plugin.py")

import install_plugin


@pytest.fixture
def plugin_dirs(tmp_path, monkeypatch):
    """Set up isolated plugins, hooks, and settings paths."""
    plugins_dir = tmp_path / "plugins"
    hooks_dir = tmp_path / "hooks"
    settings_path = tmp_path / "settings.json"
    plugins_dir.mkdir()
    hooks_dir.mkdir()
    monkeypatch.setattr(install_plugin, "PLUGINS_DIR", plugins_dir)
    monkeypatch.setattr(install_plugin, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(install_plugin, "SETTINGS_PATH", settings_path)
    return plugins_dir, hooks_dir, settings_path


def _create_plugin(plugins_dir: Path, name: str, hooks: dict | None = None) -> Path:
    """Create a minimal plugin directory with a .sh script and optional plugin.json."""
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir()
    script = plugin_dir / f"{name}.sh"
    script.write_text("#!/bin/bash\necho ok")
    if hooks is not None:
        config = {"description": f"Test plugin {name}", "hooks": hooks}
        (plugin_dir / "plugin.json").write_text(json.dumps(config))
    return plugin_dir


def test_install_plugin_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()


def test_load_plugin_config_invalid_json(plugin_dirs):
    """Verify load_plugin_config exits on malformed plugin.json."""
    plugins_dir, _, _ = plugin_dirs
    plugin_dir = plugins_dir / "bad-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("not json{{{")

    with pytest.raises(SystemExit):
        install_plugin.load_plugin_config("bad-plugin")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_install_plugin.py::test_load_plugin_config_invalid_json -v`
Expected: FAIL — currently raises `json.JSONDecodeError` instead of `SystemExit`.

- [ ] **Step 3: Add error handling to load_plugin_config**

In `scripts/install_plugin.py`, update `load_plugin_config`:

```python
def load_plugin_config(name: str) -> dict:
    """Load plugin.json metadata for a plugin."""
    config_path = PLUGINS_DIR / name / "plugin.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid plugin.json in plugins/{name}/: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_install_plugin.py::test_load_plugin_config_invalid_json -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/install_plugin.py tests/test_install_plugin.py
git commit -m "Added error handling for malformed plugin.json"
```

---

### Task 6: Add remaining install_plugin.py tests

**Files:**
- Modify: `tests/test_install_plugin.py`

- [ ] **Step 1: Write get_available_plugins and load_plugin_config tests**

Add to `tests/test_install_plugin.py`:

```python
def test_get_available_plugins(plugin_dirs):
    """Verify get_available_plugins filters directories without .sh files."""
    plugins_dir, _, _ = plugin_dirs
    _create_plugin(plugins_dir, "valid-plugin")
    # Directory without .sh files should be excluded
    (plugins_dir / "no-scripts").mkdir()
    (plugins_dir / "no-scripts" / "readme.txt").write_text("not a script")

    result = install_plugin.get_available_plugins()
    assert result == ["valid-plugin"]


def test_load_plugin_config(plugin_dirs):
    """Verify load_plugin_config returns config dict or empty dict."""
    plugins_dir, _, _ = plugin_dirs
    _create_plugin(plugins_dir, "with-config", hooks={"PermissionRequest": {"matcher": ".*"}})

    config = install_plugin.load_plugin_config("with-config")
    assert config["hooks"]["PermissionRequest"]["matcher"] == ".*"

    # Plugin without config returns empty dict
    _create_plugin(plugins_dir, "no-config")
    assert install_plugin.load_plugin_config("no-config") == {}
```

- [ ] **Step 2: Write install/remove symlink tests**

```python
def test_install_plugin_creates_symlinks(plugin_dirs):
    """Verify install_plugin symlinks .sh files into hooks directory."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    install_plugin.install_plugin("my-plugin")

    target = hooks_dir / "my-plugin.sh"
    assert target.is_symlink()
    assert target.resolve() == (plugins_dir / "my-plugin" / "my-plugin.sh").resolve()


def test_install_plugin_force_overwrites(plugin_dirs):
    """Verify --force replaces existing symlink."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    # Create existing symlink pointing elsewhere
    target = hooks_dir / "my-plugin.sh"
    target.symlink_to("/tmp")

    install_plugin.install_plugin("my-plugin", force=True)

    assert target.is_symlink()
    assert target.resolve() == (plugins_dir / "my-plugin" / "my-plugin.sh").resolve()


def test_install_plugin_conflict_without_force(plugin_dirs, capsys):
    """Verify warning when target exists without --force."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    # Create an existing symlink
    target = hooks_dir / "my-plugin.sh"
    target.symlink_to("/tmp")

    install_plugin.install_plugin("my-plugin", force=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_install_plugin_no_scripts(plugin_dirs):
    """Verify sys.exit when plugin has no .sh files."""
    plugins_dir, _, _ = plugin_dirs
    (plugins_dir / "empty-plugin").mkdir()

    with pytest.raises(SystemExit):
        install_plugin.install_plugin("empty-plugin")


def test_remove_plugin(plugin_dirs):
    """Verify remove_plugin removes symlinks and unregisters hooks."""
    plugins_dir, hooks_dir, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.install_plugin("my-plugin")
    assert (hooks_dir / "my-plugin.sh").is_symlink()

    install_plugin.remove_plugin("my-plugin")
    assert not (hooks_dir / "my-plugin.sh").exists()
```

- [ ] **Step 3: Write register/unregister hooks tests**

```python
def test_register_hooks(plugin_dirs):
    """Verify register_hooks writes hook entries to settings.json."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    event_hooks = settings["hooks"]["PermissionRequest"]
    assert len(event_hooks) == 1
    assert event_hooks[0]["matcher"] == ".*"
    assert event_hooks[0]["hooks"][0]["command"] == "bash ~/.claude/hooks/my-plugin.sh"


def test_register_hooks_dedup(plugin_dirs):
    """Verify already-registered hooks are not duplicated."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.register_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    event_hooks = settings["hooks"]["PermissionRequest"]
    assert len(event_hooks) == 1


def test_unregister_hooks(plugin_dirs):
    """Verify unregister_hooks removes hook entries from settings.json."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.unregister_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    assert "PermissionRequest" not in settings.get("hooks", {})


def test_unregister_hooks_cleans_empty(plugin_dirs):
    """Verify empty hooks dict is removed from settings entirely."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.unregister_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    assert "hooks" not in settings
```

- [ ] **Step 4: Write --all install and remove tests**

```python
def test_install_all_plugins(plugin_dirs):
    """Verify installing all available plugins."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "plugin-a", hooks={})
    _create_plugin(plugins_dir, "plugin-b", hooks={})

    for p in install_plugin.get_available_plugins():
        install_plugin.install_plugin(p)

    assert (hooks_dir / "plugin-a.sh").is_symlink()
    assert (hooks_dir / "plugin-b.sh").is_symlink()


def test_remove_all_plugins(plugin_dirs):
    """Verify removing all installed plugins."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "plugin-a", hooks={})
    _create_plugin(plugins_dir, "plugin-b", hooks={})

    for p in install_plugin.get_available_plugins():
        install_plugin.install_plugin(p)

    for p in install_plugin.get_available_plugins():
        install_plugin.remove_plugin(p)

    assert not (hooks_dir / "plugin-a.sh").exists()
    assert not (hooks_dir / "plugin-b.sh").exists()
```

- [ ] **Step 5: Run all install_plugin tests**

Run: `python -m pytest tests/test_install_plugin.py -v`
Expected: All tests pass.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_install_plugin.py
git commit -m "Added comprehensive test coverage for install_plugin.py"
```
