#!/usr/bin/env python3
"""Fetch library documentation from a URL and generate a Claude Code skill."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


def fetch_document(url: str) -> str:
    """Download text content from a URL."""
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


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


def parse_skill_response(response_text: str) -> dict:
    """Parse LLM response text into validated skill data dict.

    Strips markdown code fences, parses JSON, validates required keys.
    Calls sys.exit(1) on failure with a user-friendly error message.
    """
    # Extract JSON object by finding outermost { ... } pair.
    # Simple code-fence splitting fails when JSON content contains markdown fences.
    start = response_text.find("{")
    if start != -1:
        # Find matching closing brace by counting nesting (respecting JSON strings)
        depth = 0
        in_string = False
        escape = False
        end = start
        for i in range(start, len(response_text)):
            c = response_text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                if in_string:
                    escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        response_text = response_text[start : end + 1]

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
            max_completion_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.choices[0].message.content
        return parse_skill_response(response_text)


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


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Claude Code skill from library documentation."
    )
    parser.add_argument("--name", required=True, help="Skill name (e.g., knex, typebox)")
    parser.add_argument("--url", required=True, help="URL to the library's documentation (markdown/text)")
    parser.add_argument("--model", default=None, help="Model to use (default depends on backend)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing skill directory")
    parser.add_argument(
        "--backend",
        choices=["cli", "sdk", "openai"],
        default="openai",
        help="LLM backend: 'cli' uses claude CLI (default), 'sdk' uses Anthropic API, 'openai' uses OpenAI API",
    )
    parser.add_argument("--api-key", default=None, help="API key (used by openai backend, overrides env var)")

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

    # Generate the skill
    backends = {
        "cli": CliBackend,
        "sdk": AnthropicBackend,
        "openai": OpenAIBackend,
    }

    # Resolve model default per backend
    model = args.model or DEFAULT_MODELS[args.backend]

    if args.api_key and args.backend != "openai":
        print(f"Warning: --api-key is only used by the openai backend, ignoring.", file=sys.stderr)

    print(f"Generating skill with {model} ({args.backend} backend)...")
    if args.backend == "openai":
        backend = backends[args.backend](api_key=args.api_key)
    else:
        backend = backends[args.backend]()
    skill_content = backend.generate(model, args.name, content)

    # Write files
    write_skill(skill_dir, skill_content)
    print(f"Skill created at skills/{args.name}/")


if __name__ == "__main__":
    main()
