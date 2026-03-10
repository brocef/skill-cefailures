# skill-cefailures

A repository of Claude Code skills and hook plugins, plus tooling to create new skills from online documentation.

Each library gets a skill that provides API/pattern knowledge and debugging/troubleshooting guidance to Claude Code. Plugins provide reusable hook scripts for Claude Code.

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Create a new skill

```bash
# Using Claude CLI (default — no API key needed)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md"

# Using Anthropic SDK (requires ANTHROPIC_API_KEY)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md" --backend sdk
```

This fetches the documentation, uses Claude to analyze and split it into a SKILL.md routing layer plus topical reference docs, and writes everything to `skills/<name>/`.

By default, uses the `claude` CLI (requires [Claude Code](https://claude.com/claude-code)). Use `--backend sdk` for the Anthropic API directly (requires `pip install anthropic` and `ANTHROPIC_API_KEY`).

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

### Install a plugin

```bash
# Install a single plugin
python scripts/install_plugin.py log-permission-requests

# Install all plugins
python scripts/install_plugin.py --all

# List available plugins
python scripts/install_plugin.py --list

# Uninstall a plugin
python scripts/install_plugin.py --remove log-permission-requests
```

This creates a symlink from `~/.claude/hooks/<script>` to the plugin script in this repo.

## Repo Structure

```
skills/                     # Generated skills
  <library>/
    SKILL.md                # Routing layer (loaded on invocation)
    docs/
      <topic>.md            # Detailed reference (read on demand)
plugins/                    # Hook plugins
  <name>/
    <name>.sh               # Hook script
scripts/
  create_skill.py           # Generate skill from URL
  install_skill.py          # Symlink skills to ~/.claude/skills/
  install_plugin.py         # Symlink plugins to ~/.claude/hooks/
```

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
