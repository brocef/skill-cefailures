# Library Skill Repository Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the scripts and repo structure that let users create Claude Code library skills from online documentation and install them via symlink.

**Architecture:** Two Python scripts — `create_skill.py` (fetches docs from a URL, uses Claude API to split into SKILL.md routing layer + topical reference docs) and `install_skill.py` (symlinks skill directories into `~/.claude/skills/`). Skills live under `skills/` in a flat structure.

**Tech Stack:** Python 3, anthropic SDK, httpx

---

### Task 1: Repo scaffolding

**Files:**
- Create: `skills/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `requirements.txt`
- Remove: `knex/` (empty placeholder, skills go under `skills/`)
- Remove: `typebox/` (empty placeholder, skills go under `skills/`)

**Step 1: Create directory structure and requirements.txt**

```
skills/.gitkeep    — empty file
scripts/.gitkeep   — empty file
```

`requirements.txt`:
```
anthropic>=0.42.0
httpx>=0.27.0
```

**Step 2: Remove empty placeholder directories**

```bash
rm -rf knex/ typebox/
```

**Step 3: Commit**

```bash
git add skills/.gitkeep scripts/.gitkeep requirements.txt
git rm -r --cached knex typebox 2>/dev/null; rm -rf knex typebox
git add -A
git commit -m "scaffold: add repo structure with skills/, scripts/, requirements.txt"
```

---

### Task 2: install_skill.py

This script has no external dependencies and is simpler, so build it first.

**Files:**
- Create: `scripts/install_skill.py`

**Step 1: Write the failing test**

Create `tests/test_install_skill.py`:

```python
import subprocess
import sys

def test_install_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, "scripts/install_skill.py", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_install_skill.py -v`
Expected: FAIL — script doesn't exist yet

**Step 3: Write install_skill.py**

`scripts/install_skill.py` — pure stdlib Python:

```python
#!/usr/bin/env python3
"""Symlink library skills into ~/.claude/skills/ for Claude Code discovery."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TARGET_DIR = Path.home() / ".claude" / "skills"


def get_available_skills() -> list[str]:
    """Return names of all valid skills (directories containing SKILL.md)."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def install_skill(name: str, force: bool = False) -> None:
    """Create symlink for a single skill."""
    source = SKILLS_DIR / name
    if not (source / "SKILL.md").exists():
        print(f"Error: No SKILL.md found in skills/{name}/", file=sys.stderr)
        sys.exit(1)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    target = TARGET_DIR / name

    if target.exists() or target.is_symlink():
        if not force:
            print(f"Warning: {target} already exists. Use --force to overwrite.", file=sys.stderr)
            return
        target.unlink() if target.is_symlink() or target.is_file() else None
        if target.is_dir():
            print(f"Error: {target} is a real directory, not a symlink. Remove it manually.", file=sys.stderr)
            sys.exit(1)

    target.symlink_to(source)
    print(f"Installed: {target} -> {source}")


def remove_skill(name: str) -> None:
    """Remove symlink for a single skill."""
    target = TARGET_DIR / name
    if not target.is_symlink():
        print(f"Warning: {target} is not a symlink or doesn't exist.", file=sys.stderr)
        return
    target.unlink()
    print(f"Removed: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="Install or remove library skills for Claude Code."
    )
    parser.add_argument("name", nargs="?", help="Skill name to install")
    parser.add_argument("--all", action="store_true", help="Install all available skills")
    parser.add_argument("--remove", action="store_true", help="Remove (uninstall) the skill")
    parser.add_argument("--force", action="store_true", help="Overwrite existing symlinks")
    parser.add_argument("--list", action="store_true", help="List available skills")

    args = parser.parse_args()

    if args.list:
        skills = get_available_skills()
        if skills:
            print("Available skills:")
            for s in skills:
                installed = "✓" if (TARGET_DIR / s).is_symlink() else " "
                print(f"  [{installed}] {s}")
        else:
            print("No skills found in skills/ directory.")
        return

    if args.all:
        skills = get_available_skills()
        if not skills:
            print("No skills found in skills/ directory.")
            return
        for s in skills:
            if args.remove:
                remove_skill(s)
            else:
                install_skill(s, force=args.force)
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    if args.remove:
        remove_skill(args.name)
    else:
        install_skill(args.name, force=args.force)


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_install_skill.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/install_skill.py tests/test_install_skill.py
git commit -m "feat: add install_skill.py for symlinking skills to ~/.claude/skills/"
```

---

### Task 3: create_skill.py — URL fetching and argument parsing

Build create_skill.py incrementally. Start with the skeleton: argument parsing + URL fetching.

**Files:**
- Create: `scripts/create_skill.py`

**Step 1: Write the failing test**

Create `tests/test_create_skill.py`:

```python
import subprocess
import sys

def test_create_skill_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, "scripts/create_skill.py", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "name" in result.stdout.lower()
    assert "url" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_create_skill.py::test_create_skill_help -v`
Expected: FAIL — script doesn't exist yet

**Step 3: Write create_skill.py skeleton**

`scripts/create_skill.py`:

```python
#!/usr/bin/env python3
"""Fetch library documentation from a URL and generate a Claude Code skill."""

import argparse
import sys
from pathlib import Path

import anthropic
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

DEFAULT_MODEL = "claude-sonnet-4-6"


def fetch_document(url: str) -> str:
    """Download text content from a URL."""
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Claude Code skill from library documentation."
    )
    parser.add_argument("--name", required=True, help="Skill name (e.g., knex, typebox)")
    parser.add_argument("--url", required=True, help="URL to the library's documentation (markdown/text)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--force", action="store_true", help="Overwrite existing skill directory")

    args = parser.parse_args()

    # Validate skill doesn't already exist
    skill_dir = SKILLS_DIR / args.name
    if skill_dir.exists() and not args.force:
        print(f"Error: skills/{args.name}/ already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    # Fetch the document
    print(f"Fetching documentation from {args.url}...")
    try:
        content = fetch_document(args.url)
    except httpx.HTTPError as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(content)} characters.")

    # Check for API key
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    # Generate the skill
    print(f"Generating skill with {args.model}...")
    skill_content = generate_skill(client, args.model, args.name, content)

    # Write files
    write_skill(skill_dir, skill_content)
    print(f"Skill created at skills/{args.name}/")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_create_skill.py::test_create_skill_help -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "feat: add create_skill.py skeleton with arg parsing and URL fetching"
```

---

### Task 4: create_skill.py — LLM generation logic

Add the `generate_skill` and `write_skill` functions that call Claude API.

**Files:**
- Modify: `scripts/create_skill.py`

**Step 1: Write the generate_skill function**

Add to `scripts/create_skill.py` before `main()`:

```python
ANALYSIS_PROMPT = """\
You are generating a Claude Code skill for the "{name}" library.

Below is the library's documentation. Analyze it and produce a structured skill.

Return your response as a JSON object with this exact structure:
{{
  "library_description": "One sentence describing what the library does",
  "trigger_description": "Use when ... (conditions that should trigger this skill)",
  "when_to_use": ["bullet 1", "bullet 2", ...],
  "key_patterns": ["pattern 1: explanation", "pattern 2: explanation", ...],
  "topics": [
    {{
      "filename": "topic-name.md",
      "title": "Topic Title",
      "description": "Brief description for the routing table",
      "content": "Full markdown content for this reference doc"
    }}
  ]
}}

Guidelines:
- Split the documentation into 3-8 topical reference files
- Each topic should be self-contained and focused
- Always include a "troubleshooting.md" topic with common errors and gotchas
- key_patterns should be 3-5 critical things a developer MUST know
- trigger_description must ONLY describe when to use, never summarize the workflow
- Preserve code examples from the original documentation
- Do not invent information not present in the source documentation

Documentation:
{content}
"""


def generate_skill(client: anthropic.Anthropic, model: str, name: str, content: str) -> dict:
    """Call Claude API to analyze docs and generate structured skill content."""
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": ANALYSIS_PROMPT.format(name=name, content=content),
            }
        ],
    )

    import json
    response_text = response.content[0].text

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    return json.loads(response_text)


def build_skill_md(name: str, skill_data: dict) -> str:
    """Build the SKILL.md routing layer from structured data."""
    lines = [
        "---",
        f"name: {name}",
        f"description: {skill_data['trigger_description']}",
        "---",
        "",
        f"# {name}",
        "",
        skill_data["library_description"],
        "",
        "## When to Use",
        "",
    ]

    for item in skill_data["when_to_use"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Reference", ""])
    lines.append("Read the relevant doc based on your task:")
    lines.append("")

    for topic in skill_data["topics"]:
        lines.append(f"- **{topic['title']}** — `docs/{topic['filename']}` — {topic['description']}")

    lines.extend(["", "## Key Patterns", ""])

    for pattern in skill_data["key_patterns"]:
        lines.append(f"- {pattern}")

    lines.append("")
    return "\n".join(lines)


def write_skill(skill_dir: Path, skill_data: dict) -> None:
    """Write SKILL.md and docs/*.md files to disk."""
    import shutil

    # Clean existing if present
    if skill_dir.exists():
        shutil.rmtree(skill_dir)

    docs_dir = skill_dir / "docs"
    docs_dir.mkdir(parents=True)

    # Write SKILL.md
    skill_md = build_skill_md(skill_dir.name, skill_data)
    (skill_dir / "SKILL.md").write_text(skill_md)

    # Write topic docs
    for topic in skill_data["topics"]:
        (docs_dir / topic["filename"]).write_text(topic["content"])
```

**Step 2: Write an integration test (mocked)**

Add to `tests/test_create_skill.py`:

```python
import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

# Append scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


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
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_create_skill.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add scripts/create_skill.py tests/test_create_skill.py
git commit -m "feat: add LLM generation logic to create_skill.py"
```

---

### Task 5: README.md

**Files:**
- Create: `README.md`

**Step 1: Write README.md**

```markdown
# skill-cefailures

A repository of Claude Code skills for specific libraries, plus tooling to create new skills from online documentation.

Each library gets a skill that provides API/pattern knowledge and debugging/troubleshooting guidance to Claude Code.

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create a new skill

```bash
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md"
```

This fetches the documentation, uses Claude to analyze and split it into a SKILL.md routing layer plus topical reference docs, and writes everything to `skills/<name>/`.

Requires `ANTHROPIC_API_KEY` environment variable.

### Install a skill

```bash
# Install a single skill
python scripts/install_skill.py knex

# Install all skills
python scripts/install_skill.py --all

# List available skills
python scripts/install_skill.py --list

# Uninstall a skill
python scripts/install_skill.py --remove knex
```

This creates a symlink from `~/.claude/skills/<name>` to the skill in this repo.

## Repo Structure

```
skills/                     # Generated skills
  <library>/
    SKILL.md                # Routing layer (loaded on invocation)
    docs/
      <topic>.md            # Detailed reference (read on demand)
scripts/
  create_skill.py           # Generate skill from URL
  install_skill.py          # Symlink skills to ~/.claude/skills/
```

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```

---

### Task 6: Clean up and verify

**Step 1: Remove empty placeholder directories**

Verify `knex/` and `typebox/` are removed (from Task 1). If still present:

```bash
rm -rf knex/ typebox/
git add -A
```

**Step 2: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: ALL PASS

**Step 3: Verify script help output**

```bash
python scripts/create_skill.py --help
python scripts/install_skill.py --help
```

**Step 4: Final commit if any remaining changes**

```bash
git status
# If anything uncommitted:
git add -A
git commit -m "chore: clean up placeholder directories"
```
