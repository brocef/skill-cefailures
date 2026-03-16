# High-Impact Improvements Design

**Date:** 2026-03-16
**Status:** Approved

## Overview

Three highest-impact improvements identified during project review:

1. Fix backend default mismatch (bug)
2. Add HTML-to-markdown content extraction for `fetch_document()`
3. Fill test coverage gaps for `install_skill.py`, `install_plugin.py`, and `AnthropicBackend`

## 1. Fix Backend Default Text

### Problem

`create_skill.py:329` sets `default="openai"` for the `--backend` argument, but the argparse help string says `'cli' uses claude CLI (default)`. CLAUDE.md also documents `cli` as the default. The actual default (`openai`) is correct — it's the most capable backend and the one the project owner uses — the documentation is wrong.

### Changes

- Update argparse help string at `create_skill.py:330` to indicate `openai` is the default
- Update CLAUDE.md command examples to reflect `openai` as the default backend
- Fix stale "cli (default)" references in `AnthropicBackend` ImportError message (line 204) and `OpenAIBackend` ImportError message (line 238)
- Update CLAUDE.md Repository Structure section to include `install_plugin.py` and `test_install_plugin.py`

## 2. HTML Content Extraction

### Problem

`fetch_document()` returns raw `response.text` regardless of content type. Most library documentation URLs serve HTML, meaning the LLM receives raw HTML with nav bars, footers, scripts, and tags — wasting tokens and degrading generation quality.

### Approach

Use the `html2text` library to convert HTML responses to clean markdown.

### Changes

- Add `html2text` to `requirements.txt` as a required dependency
- In `fetch_document()`:
  - Check the `Content-Type` response header for `text/html`
  - If HTML (check with `startswith("text/html")` to handle charset params like `text/html; charset=utf-8`): convert to markdown via `html2text` (preserve links, ignore images)
  - If text/plain or other: return as-is
- Add tests:
  - HTML input is converted to markdown
  - Plain text input passes through unchanged

### Configuration

`html2text` settings:
- `ignore_links = False` (preserve links — docs reference other pages)
- `ignore_images = True` (images aren't useful for skill generation)
- `body_width = 0` (no line wrapping — let the LLM handle formatting)

## 3. Test Coverage

### Problem

- `install_skill.py` has only a `--help` smoke test
- `install_plugin.py` has zero tests
- `AnthropicBackend` has no tests (while `CliBackend` and `OpenAIBackend` do)

### Approach

All filesystem tests use `tmp_path` fixture with monkeypatched module-level path constants (e.g., `monkeypatch.setattr(install_plugin, "SETTINGS_PATH", tmp_path / "settings.json")`) to avoid touching real `~/.claude/`. Constants are patched on the module object since they are resolved at import time.

### Test Plan

#### `test_install_skill.py` (new tests)

- `test_get_available_skills` — create skill dirs with/without SKILL.md, verify filtering
- `test_install_skill_creates_symlink` — verify symlink creation in target dir
- `test_install_skill_force_overwrites` — verify `--force` replaces existing symlink
- `test_install_skill_conflict_without_force` — verify warning on existing target
- `test_install_skill_real_dir_exits` — verify sys.exit when target is a real directory
- `test_install_skill_missing_skill_md` — verify sys.exit for invalid skill
- `test_remove_skill` — verify symlink removal
- `test_remove_skill_not_symlink` — verify warning for non-symlink target
- `test_list_skills` — verify `--list` output shows available skills with install status
- `test_install_all` — verify `--all` installs every available skill
- `test_remove_all` — verify `--all --remove` removes every installed skill

#### `test_install_plugin.py` (new file)

- `test_install_plugin_help` — smoke test
- `test_get_available_plugins` — create plugin dirs with/without .sh files, verify filtering
- `test_load_plugin_config` — valid JSON, missing file returns empty dict
- `test_load_plugin_config_invalid_json` — malformed plugin.json currently raises unhandled `json.JSONDecodeError`; add graceful error handling (`sys.exit(1)` with message) consistent with project conventions, then test for `SystemExit`
- `test_install_plugin_creates_symlinks` — verify .sh files symlinked to hooks dir
- `test_install_plugin_force_overwrites` — verify `--force` replaces existing
- `test_remove_plugin` — verify symlink removal and hook unregistration
- `test_register_hooks` — verify settings.json is updated with hook entries
- `test_register_hooks_dedup` — verify already-registered hooks are skipped
- `test_unregister_hooks` — verify hook entries are removed from settings.json
- `test_unregister_hooks_cleans_empty` — verify empty hooks dict is removed from settings
- `test_install_all_plugins` — verify `--all` installs every available plugin
- `test_remove_all_plugins` — verify `--all --remove` removes every installed plugin

#### `test_create_skill.py` (new tests)

- `test_anthropic_backend_success` — mock Anthropic client, verify API call and response parsing
- `test_anthropic_backend_missing_api_key` — verify sys.exit without ANTHROPIC_API_KEY
- `test_fetch_document_html_conversion` — verify HTML is converted to markdown
- `test_fetch_document_plain_text_passthrough` — verify plain text is returned unchanged

## Files Modified

- `scripts/create_skill.py` — fix help text, update `fetch_document()`
- `CLAUDE.md` — fix default backend documentation
- `requirements.txt` — add `html2text`
- `tests/test_create_skill.py` — add AnthropicBackend and fetch_document tests
- `tests/test_install_skill.py` — add comprehensive tests
- `tests/test_install_plugin.py` — new file with comprehensive tests
