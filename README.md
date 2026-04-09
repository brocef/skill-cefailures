# skill-cefailures

A Claude Code plugin providing skills for specific libraries, plus tooling to create new skills from online documentation.

Each library gets a skill that provides API/pattern knowledge and debugging/troubleshooting guidance to Claude Code.

## Installation

### As a plugin (recommended)

In Claude Code, run:

```
/plugin marketplace add brocef/skill-cefailures
/plugin install skill-cefailures
```

Skills are available as `/skill-cefailures:<skill-name>` (e.g. `/skill-cefailures:ieee`).

### Local development

If you've cloned the repo, you can load it directly:

```bash
claude --plugin-dir /path/to/skill-cefailures
```

### Via symlinks (legacy)

```bash
pip install -r requirements.txt

# Install a single skill
python scripts/install_skill.py knex

# Install all skills
python scripts/install_skill.py --all

# List available skills
python scripts/install_skill.py --list

# Uninstall a skill
python scripts/install_skill.py --remove knex

# Uninstall all skills
python scripts/install_skill.py --remove-all
```

This creates symlinks from `~/.claude/skills/<name>` to the skills in this repo.

## Creating a new skill

```bash
pip install -r requirements.txt

# Using Claude CLI (default — no API key needed)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md"

# Using Anthropic SDK (requires ANTHROPIC_API_KEY)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md" --backend sdk
```

This fetches the documentation, uses Claude to analyze and split it into a SKILL.md routing layer plus topical reference docs, and writes everything to `skills/<name>/`.

By default, uses the `claude` CLI (requires [Claude Code](https://claude.com/claude-code)). Use `--backend sdk` for the Anthropic API directly (requires `pip install anthropic` and `ANTHROPIC_API_KEY`).

## Repo Structure

```
skills/                       # Skills
  <library>/
    SKILL.md                  # Routing layer (loaded on invocation)
    docs/
      <topic>.md              # Detailed reference (read on demand)
scripts/
  create_skill.py             # Generate skill from URL
  install_skill.py            # Symlink skills to ~/.claude/skills/
  analyze_permissions.py      # Analyze permission request logs
  log-permission-requests.sh  # Permission logging hook script
tests/
  test_create_skill.py
  test_install_skill.py
  test_analyze_permissions.py
```

## MCP Message Broker

A lightweight MCP server that lets two Claude Code instances on the same machine hold structured conversations. Messages are persisted as JSON files so conversations survive restarts.

### Setup

Install the broker into each project that needs it, giving each a unique identity:

```bash
python scripts/install_broker.py /path/to/project-a --identity agent_a
python scripts/install_broker.py /path/to/project-b --identity agent_b
```

This adds a `broker` entry to each project's `.claude/settings.json`. Restart Claude Code for the new MCP server to take effect.

To point both instances at a custom storage directory:

```bash
python scripts/install_broker.py /path/to/project --identity agent_a --storage-dir /shared/conversations
```

To remove the broker from a project:

```bash
python scripts/install_broker.py /path/to/project --remove
```

### Starting a conversation between agents

Once the broker is installed in both projects, you can tell either agent to start a conversation. In either Claude Code instance, ask it to create a conversation with a seed message explaining what the agents should discuss:

```
You have a broker MCP tool. Create a conversation with agent_b about adding
a Redis caching layer to the API. Explain what you need in the first message.
```

The agent will use `create_conversation` to start the dialogue. The other agent can then be told to check for new conversations:

```
Check the broker for any new conversations and respond to them.
```

The agents will use `list_conversations`, `read_new_messages`, and `send_message` to carry on the conversation autonomously.

### Joining a conversation as a human

Use the REPL CLI to participate in conversations alongside AI agents:

```bash
python scripts/broker_cli.py
python scripts/broker_cli.py --identity brian    # default identity is "user"
```

This opens an interactive session with two modes:

**Lobby** (`broker>` prompt) — manage conversations:
- `list` — show all conversations with unread counts
- `create <topic>` — start a new conversation (prompts for an optional seed message)
- `join <id>` — enter a conversation
- `exit` — quit

**Conversation** (`<id>>` prompt) — read and send messages:
- `read` — show new messages
- `close` — close the conversation
- `back` — return to lobby
- Anything else is sent as a message

Example workflow — creating a conversation for two agents to discuss:

```
$ python scripts/broker_cli.py --identity brian
broker> create Design a caching layer
  Created a1b2c3
  Seed message (Enter to skip): I need agent_a and agent_b to collaborate on
  adding Redis caching to the API. Focus on the hot path in /api/v1/search.
  Sent msg-d4e5f6
broker> join a1b2c3
a1b2c3> read
  [agent_a] I'll start by profiling the search endpoint...
  [agent_b] I can handle the Redis connection config.
a1b2c3> Make sure to add cache invalidation on writes
  Sent msg-f7e8d9
a1b2c3> back
broker> exit
```

### MCP tools reference

Once configured, each Claude Code instance has access to these tools:

| Tool | Description |
|------|-------------|
| `create_conversation(topic, content?)` | Start a new conversation, optionally with a seed message |
| `send_message(conversation_id, content)` | Send a message |
| `read_new_messages(conversation_id)` | Read messages you haven't seen yet |
| `list_conversations(status?)` | List conversations (optionally filter by `"open"` / `"closed"`) |
| `close_conversation(conversation_id)` | Mark a conversation as read-only |

Conversations are stored as JSON files in `~/.mcp-broker/conversations/` by default.

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
