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
  broker_server.py            # Broker server: state, routing, persistence
  broker_client.py            # Async socket client for the broker
  broker_cli.py               # REPL CLI (server mode + client mode)
  mcp_broker.py               # MCP server (connects to broker via socket)
  install_broker.py           # Install broker into a project's .mcp.json
tests/
  test_create_skill.py
  test_install_skill.py
  test_analyze_permissions.py
  test_broker_server.py
  test_broker_transport.py
  test_broker_client.py
  test_broker_cli.py
  test_broker_e2e.py
  test_mcp_broker.py
  test_install_broker.py
```

## MCP Message Broker

A chatroom-like MCP server that lets Claude Code agents and a human talk to each other in real time. Messages route through a Unix domain socket for instant delivery and are persisted to disk so conversations survive restarts.

### Architecture

A central broker server runs as a socket hub. Each Claude Code agent connects to it via its MCP server process. A human can participate through the built-in REPL or a separate client terminal.

```
Claude A ◄─stdio─► mcp_broker.py ◄──┐
                                     │ Unix domain
Claude B ◄─stdio─► mcp_broker.py ◄──┤ socket
                                     │
        broker_cli.py --server  ◄────┘
        (socket server + REPL)
```

### 1. Start the broker server

The broker server must be running before agents or clients can connect:

```bash
python scripts/broker_cli.py --server
python scripts/broker_cli.py --server --identity brian    # default identity is "user"
```

This starts the socket server at `~/.mcp-broker/broker.sock` and opens an interactive REPL where you can participate in conversations. Conversations are persisted to `~/.mcp-broker/conversations/`.

### 2. Install the MCP broker into agent projects

Install the broker into each project that needs it, giving each a unique identity:

```bash
python scripts/install_broker.py /path/to/project-a --identity agent_a
python scripts/install_broker.py /path/to/project-b --identity agent_b
```

This adds a `broker` entry to each project's `.mcp.json`. Restart Claude Code for the new MCP server to take effect. The broker server must be running when agents start.

To use a custom socket path:

```bash
python scripts/install_broker.py /path/to/project --identity agent_a --socket /custom/broker.sock
```

To remove the broker from a project:

```bash
python scripts/install_broker.py /path/to/project --remove
```

### 3. Start a conversation

From the broker server REPL, create a conversation and seed it with instructions for the agents:

```
broker> create Design a caching layer
  Created a1b2c3
  Seed message (Enter to skip): I need agent_a and agent_b to collaborate on
  adding Redis caching to the API. Focus on the hot path in /api/v1/search.
  Sent msg-d4e5f6
```

Then tell each agent to check for conversations:

```
You have a broker MCP tool. Check for new conversations and respond to them.
```

Agents use `list_conversations`, `read_new_messages`, and `send_message` to participate. Messages from agents appear in your REPL in real time.

### 4. Participate in conversations

The REPL has two modes:

**Lobby** (`broker>` prompt):
- `list` — show all conversations with unread counts
- `create <topic>` — start a new conversation (prompts for an optional seed message)
- `join <id>` — enter a conversation
- `exit` — quit

**Conversation** (`<id>>` prompt):
- `read` — show message history
- `members` — show who's in the conversation
- `leave` — leave the conversation and return to lobby
- `close` — close the conversation (read-only for everyone)
- `back` — return to lobby without leaving (you still receive messages)
- Anything else is sent as a message

Incoming messages from agents print automatically when you're in a conversation — no need to poll.

### 5. Connect from a separate terminal (client mode)

You can also join from another terminal without running the server:

```bash
python scripts/broker_cli.py --identity observer
```

This connects to the running broker server as a client with the same REPL interface.

### System messages

The broker tracks conversation membership. When someone joins or leaves a conversation, a system message is broadcast to all members:

```
  * agent_a joined
  * agent_b left
```

### MCP tools reference

Each Claude Code agent has access to these tools:

| Tool | Description |
|------|-------------|
| `create_conversation(topic, content?)` | Start a new conversation, optionally with a seed message (auto-joins) |
| `send_message(conversation_id, content)` | Send a message (auto-joins) |
| `read_new_messages(conversation_id)` | Read messages you haven't seen yet |
| `join_conversation(conversation_id)` | Explicitly join a conversation |
| `leave_conversation(conversation_id)` | Leave a conversation |
| `list_conversations(status?)` | List conversations (optionally filter by `"open"` / `"closed"`) |
| `list_members(conversation_id)` | See who's currently in a conversation |
| `close_conversation(conversation_id)` | Mark a conversation as read-only for everyone |

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
