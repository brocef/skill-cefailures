# skill-cefailures

Agent skills for specific libraries, plus tooling to create new skills from online documentation. The skills can be used from Claude Code and Codex.

Each library gets a skill that provides API/pattern knowledge and debugging/troubleshooting guidance to an AI coding agent.

## Installation

### As a plugin (recommended)

In Claude Code, run:

```
/plugin marketplace add brocef/skill-cefailures
/plugin install skill-cefailures
```

Skills are available as `/skill-cefailures:<skill-name>` (e.g. `/skill-cefailures:brain-style`).

In Codex, add the marketplace and install the plugin:

```bash
codex plugin marketplace add brocef/skill-cefailures --ref main
codex plugin add skill-cefailures@skill-cefailures
```

Skills are available as `skill-cefailures:<skill-name>` in Codex sessions after starting a new thread.

### Local development

If you've cloned the repo, you can load it directly:

```bash
claude --plugin-dir /path/to/skill-cefailures
```

## Creating a new skill

```bash
pip install -r requirements.txt

# Using OpenAI (default — requires OPENAI_API_KEY)
python scripts/create_skill.py --name redis --url "https://example.com/redis-docs.md"

# Using Anthropic SDK (requires ANTHROPIC_API_KEY)
python scripts/create_skill.py --name redis --url "https://example.com/redis-docs.md" --backend sdk

# Using the local Claude CLI (no API key needed; requires Claude Code installed)
python scripts/create_skill.py --name redis --url "https://example.com/redis-docs.md" --backend cli
```

This fetches the documentation, uses an LLM to analyze and split it into a SKILL.md routing layer plus topical reference docs, and writes everything to `skills/<name>/`.

Backend choices:

- `--backend openai` (default) — uses the OpenAI API. Requires `pip install openai` and `OPENAI_API_KEY` (or `--api-key`).
- `--backend sdk` — uses the Anthropic API directly. Requires `pip install anthropic` and `ANTHROPIC_API_KEY`.
- `--backend cli` — shells out to the local `claude` CLI (requires [Claude Code](https://claude.com/claude-code)).

Optional flags: `--model <id>` overrides the per-backend default model; `--force` overwrites an existing skill directory.

## Repo Structure

```
.agents/plugins/
  marketplace.json            # Codex marketplace listing
.claude-plugin/
  plugin.json                 # Plugin manifest (name, version, skills/commands paths)
  marketplace.json            # Marketplace listing
.codex-plugin/
  plugin.json                 # Codex plugin manifest
commands/
  brain-style/                # /skill-cefailures:brain-style:* commands
  permissions-auditor/        # /skill-cefailures:permissions-auditor:* commands
skills/                       # One directory per skill
  brain-style/
  capabilities-sdlc/
  report/
  <name>/
    SKILL.md                  # Routing layer (loaded on invocation)
    docs/
      <topic>.md              # Detailed reference (read on demand)
plugins/
  skill-cefailures -> ..      # Codex marketplace pointer to the repo-root plugin
scripts/
  create_skill.py             # Generate skill from URL
  analyze_permissions.py      # Analyze permission request logs
  apply_permissions.py        # Apply curated permission lists to settings.json
  log-permission-requests.sh  # Permission logging hook script
tests/                        # pytest suite
docs/
  release-notes/              # Per-version user-facing notes (vX.Y.Z.md + upcoming.md)
  changelogs/                 # Per-version developer changelogs
  plans/                      # Design and implementation documents
AGENTS.md                     # Project instructions for Codex and compatible agents
CLAUDE.md                     # Symlink to AGENTS.md for Claude Code compatibility
requirements.txt              # Runtime dependencies
requirements-dev.txt          # Runtime + test dependencies (use this to run the suite)
```

## Skills

| Skill | Purpose |
|-------|---------|
| `brain-style` | Code style preferences across TypeScript naming, types, and resource-oriented HTTP route design. |
| `capabilities-sdlc` | Project-neutral user-capability documentation conventions for co-located or centralized files, with a planning gate, contradiction-detection rule, and optional multi-repo coordination. |
| `report` | How to report a bug, issue, or suggestion about this plugin — files a GitHub issue on this repo, with a ready-to-fill skeleton for each kind of report. |

## Slash Commands

This plugin ships slash commands under `commands/` (registered via `plugin.json`). Commands are for workflows that are *purely* user-explicit — they replace the auto-trigger metadata of skills, which keeps skill descriptions narrow and saves session context.

| Command | Purpose |
|---------|---------|
| `/skill-cefailures:brain-style:review` | Architecture review of a file/function/class against decomposition, file-size, and redundancy guidelines. |
| `/skill-cefailures:brain-style:agents-md` | Review or author a project's `AGENTS.md` against the minimal-routing principle and required-sections checklist, and ensure `CLAUDE.md` is a symlink to it. |
| `/skill-cefailures:permissions-auditor:install` | Install the permission-logging hook so future permission prompts are captured for later triage. |
| `/skill-cefailures:permissions-auditor:analyze` | Analyze logged permission requests, present recurring patterns, and triage them into allow/deny/manual-review rules. |

## How Skills Work

When an agent invokes a library skill:

1. **SKILL.md** is loaded — gives the agent a brief overview and a routing table to reference docs in `docs/`. The frontmatter `description` field acts as the skill's invocation criteria.
2. The agent **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
