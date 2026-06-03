# AGENTS.md

## Generic instructions

- Git commit messages should not include any co-authoring content
- After completing a major set of changes, offer to cut a new version following the `skill-cefailures:documentation-sync` skill's "Version Management" section. Project-specific note: the plugin version is carried in **all** version-bearing plugin metadata files: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `.codex-plugin/plugin.json` — bump them together. Use `minor` (not just `patch`) for new skills or significant feature work.
- All changes should remain compatible with both Claude Code and Codex unless the user explicitly scopes the work to one agent. When adding or changing plugin metadata, skills, commands, or install instructions, update both agent surfaces or document why one surface is intentionally unaffected.

## Documentation Sync

Before reporting any code change complete, invoke the `skill-cefailures:documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes; plain language, no jargon
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
- `docs/FOLLOWUPS.md` [Any-Code-Change] — Standing log of deferred follow-up items; prepend an entry (commit range, branch, date) when feature work leaves code-related TODOs; annotate items as completed (strikethrough + date) when finished — do not delete

## Project Overview

A repository of agent skills for specific libraries, plus tooling to generate new skills from online documentation. Each skill provides API/pattern knowledge and troubleshooting guidance to Claude Code and Codex.

## Tech Stack

- **Language:** Python 3 (type hints throughout)
- **Dependencies:** `httpx` and `html2text` (required), `anthropic` and `openai` (optional, per backend)
- **Tests:** pytest
- **Package manager:** pip

## Repository Structure

```
scripts/
  create_skill.py           # Generate a skill from a documentation URL
  analyze_permissions.py    # Analyze permission request logs
  log-permission-requests.sh # Permission logging hook script
skills/
  <library>/
    SKILL.md                # Routing layer (loaded on invocation)
    docs/<topic>.md         # Detailed reference (read on demand)
tests/
  test_create_skill.py
  test_analyze_permissions.py
docs/plans/                 # Design and implementation documents
```

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Create a new skill (default: openai backend)
python scripts/create_skill.py --name <lib> --url "<docs-url>"

# Create a skill with a specific backend
python scripts/create_skill.py --name <lib> --url "<url>" --backend sdk    # Anthropic API
python scripts/create_skill.py --name <lib> --url "<url>" --backend openai # OpenAI API
```

## Code Conventions

- Type hints on all function signatures
- Docstrings on all public functions and classes
- ABC pattern for backend extensibility (`Backend` base class in `create_skill.py`)
- Errors print to stderr and `sys.exit(1)` — no exception propagation in CLI paths
- Tests use `unittest.mock` (patch/MagicMock) and pytest fixtures (`tmp_path`)
- Scripts are imported in tests via `sys.path.insert`; keep scripts importable (guard `if __name__ == "__main__"`)

## Architecture Notes

- **Multi-backend system:** `CliBackend` (subprocess to `claude` CLI), `AnthropicBackend` (Anthropic SDK), `OpenAIBackend` (OpenAI SDK). All inherit from `Backend` ABC.
- **Skill format:** SKILL.md is a routing layer with frontmatter, overview, triggers, a reference table pointing to `docs/*.md`, and inlined key patterns. Docs files contain full API details and examples.
