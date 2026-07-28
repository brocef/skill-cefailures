# AGENTS.md

## Generic instructions

- Git commit messages should not include any co-authoring content
- After completing a substantial set of changes, offer the four outcomes in the `tcw:documentation-sync` skill's "When to offer version and changelog options" section: `major`, `minor`, or `patch`, or keep the current version and update the applicable changelog files. See `## Versioning` below for how this project cuts one.
- All changes should remain compatible with both Claude Code and Codex unless the user explicitly scopes the work to one agent. When adding or changing plugin metadata, skills, commands, or install instructions, update both agent surfaces or document why one surface is intentionally unaffected.

## Documentation Sync

Before reporting any code change complete, invoke the `tcw:documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

That skill ships in the **TCW plugin**, not this one — install TCW for this directive to resolve. This project used to carry its own copy; it was removed in favor of TCW's.

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes; plain language, no jargon
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
- `docs/FOLLOWUPS.md` [Any-Code-Change] — Standing log of deferred follow-up items; prepend an entry (commit range, branch, date) when feature work leaves code-related TODOs; annotate items as completed (strikethrough + date) when finished — do not delete

## Versioning

This project has no version-cut script; cut by hand following these steps.

1. **Bump all three version-bearing files together** — a desynced version is its own kind of bug:
   - `.claude-plugin/plugin.json`
   - `.claude-plugin/marketplace.json` (the `version` inside `plugins[0]`)
   - `.codex-plugin/plugin.json`
2. **Rotate the working files**: `git mv docs/release-notes/upcoming.md docs/release-notes/v{version}.md` and the same for `docs/changelogs/`, then recreate each `upcoming.md` containing only `# Upcoming`.
3. **Commit** the bump and the rotated docs together: `chore(release): cut v{version}`.
4. **Tag** that commit: `git tag v{version}`. Pushing a tag is publishing — ask first.

Bump size: use `minor` (not `patch`) for new skills, removed skills, or significant feature work.

## Project Overview

A Claude Code / Codex plugin shipping two surfaces: **skills** (library API/pattern knowledge + troubleshooting) and **slash commands** (`commands/`). It also includes tooling to generate new skills from online documentation. The README is the authoritative human-facing catalog — route to its **Skills** and **Slash Commands** sections rather than restating them here.

Installed skills (`skills/<name>/`): `brain-style`, `capabilities-sdlc`, `report`. Slash commands (`commands/<group>/`): `brain-style`, `permissions-auditor`.

## Tech Stack

- **Language:** Python 3 (type hints throughout)
- **Dependencies:** `httpx`, `html2text` (required); `anthropic` and `openai` (optional, per skill-generation backend)
- **Tests:** pytest
- **Package manager:** pip

## Repository Structure

```
scripts/
  create_skill.py            # Generate a skill from a documentation URL
  analyze_permissions.py     # Permissions-auditor: analyze logged requests
  apply_permissions.py       # Permissions-auditor: apply triaged rules
  log-permission-requests.sh # Permission-logging hook script
skills/<name>/
  SKILL.md                   # Routing layer (loaded on invocation)
  docs/<topic>.md            # Detailed reference (read on demand)
commands/<group>/*.md        # Slash-command definitions
data/                        # Bundled data (e.g. recommended-permissions.json)
.claude-plugin/ + .codex-plugin/  # Plugin metadata (version-bearing — bump together)
tests/                       # pytest (test_create_skill, test_analyze_permissions)
docs/{plans,release-notes,changelogs,inbox}/
```

## Common Commands

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install everything needed to run the tests (runtime + pytest + both backend SDKs)
pip install -r requirements-dev.txt

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
