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
  broker/
    SKILL.md                  # Broker skill routing layer
    docs/
      usage.md                # CLI reference
      setup.md                # Installation instructions
scripts/
  create_skill.py             # Generate skill from URL
  install_skill.py            # Symlink skills to ~/.claude/skills/
  analyze_permissions.py      # Analyze permission request logs
  log-permission-requests.sh  # Permission logging hook script
  broker_server.py            # Broker server: state, routing, persistence
  broker_client.py            # Async socket client for the broker
  broker_cli.py               # Broker CLI: server, REPL, and one-shot subcommands
tests/
  test_create_skill.py
  test_install_skill.py
  test_analyze_permissions.py
  test_broker_server.py
  test_broker_transport.py
  test_broker_client.py
  test_broker_cli.py
  test_broker_e2e.py
```

## Message Broker

A chatroom-like tool that lets Claude Code agents and a human talk to each other in real time. Messages route through a Unix domain socket for instant delivery and are persisted to disk so conversations survive restarts.

### Architecture

A central broker server runs as a socket hub. Each Claude Code agent calls the broker CLI to send and receive messages. A human can participate through the built-in REPL or a separate client terminal.

```
Claude A ──Bash──► broker send/read/list ◄──┐
                                             │ Unix domain
Claude B ──Bash──► broker send/read/list ◄──┤ socket
                                             │
                    broker server        ◄───┘
                    (socket server + REPL)
```

### 1. Start the broker server

The broker server must be running before agents or clients can connect:

```bash
python scripts/broker_cli.py --server
python scripts/broker_cli.py --server --identity brian    # default identity is "user"
```

This starts the socket server at `~/.mcp-broker/broker.sock` and opens an interactive REPL where you can participate in conversations. Conversations are persisted to `~/.mcp-broker/conversations/`.

### 2. Install the broker CLI

Create a symlink so `broker` is available in your `$PATH`:

```bash
ln -s /path/to/skill-cefailures/scripts/broker_cli.py /usr/local/bin/broker
chmod +x /path/to/skill-cefailures/scripts/broker_cli.py
```

Add `Bash(broker:*)` to your Claude Code allowedTools so agents can call the broker without permission prompts.

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
You have a broker CLI. Check for conversations with `broker list --identity <agent-name>` and respond to any messages.
```

Agents use `broker list`, `broker read`, and `broker send` to participate. Messages from agents appear in your REPL in real time.

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

### CLI reference

| Command | Description |
|---------|-------------|
| `broker create --identity NAME TOPIC [--content MSG]` | Start a new conversation, optionally with a seed message (auto-joins) |
| `broker send --identity NAME CONV_ID CONTENT` | Send a message (auto-joins) |
| `broker read --identity NAME CONV_ID` | Read messages you haven't seen yet |
| `broker join --identity NAME CONV_ID` | Explicitly join a conversation |
| `broker leave --identity NAME CONV_ID` | Leave a conversation |
| `broker list --identity NAME [--status open\|closed]` | List conversations |
| `broker members --identity NAME CONV_ID` | See who's in a conversation |
| `broker close --identity NAME CONV_ID` | Mark a conversation as read-only |

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
