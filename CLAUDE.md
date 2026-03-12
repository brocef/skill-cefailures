# CLAUDE.md

## Generic instructions

- Git commit messages should not include any co-authoring content

## Project Overview

A repository of Claude Code skills for specific libraries, plus tooling to generate new skills from online documentation. Each skill provides API/pattern knowledge and troubleshooting guidance to Claude Code.

## Tech Stack

- **Language:** Python 3 (type hints throughout)
- **Dependencies:** `httpx` (required), `anthropic` and `openai` (optional, per backend)
- **Tests:** pytest
- **Package manager:** pip

## Repository Structure

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

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Create a new skill (default: claude CLI backend)
python scripts/create_skill.py --name <lib> --url "<docs-url>"

# Create a skill with a specific backend
python scripts/create_skill.py --name <lib> --url "<url>" --backend sdk    # Anthropic API
python scripts/create_skill.py --name <lib> --url "<url>" --backend openai # OpenAI API

# List / install / remove skills
python scripts/install_skill.py --list
python scripts/install_skill.py <name>        # install one
python scripts/install_skill.py --all         # install all
python scripts/install_skill.py --remove <name>
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
- **Symlink installation:** `install_skill.py` symlinks into `~/.claude/skills/` so repo updates propagate automatically.
