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
  test_broker_client.py
  test_broker_dm_cli.py
  test_broker_dm_e2e.py
  test_broker_dm_server.py
  test_broker_format.py
  test_broker_identity.py
  test_broker_repl.py
  test_broker_storage.py
  test_broker_transport.py
```

## Message Broker

A direct-message bus that lets Claude Code agents (and a human) talk to each other in real time. Every participant has a persistent identity and a per-identity inbox on disk, so messages survive restarts and can be addressed without any kind of conversation/room setup.

### Architecture

A single broker server runs as a Unix-domain-socket hub on the host. Every participant — humans, orchestrators, and individual repo-bound agents — connects to the same socket as a named **identity**. Sending a message is a simple call: `broker send --to <identity> "<text>"`. The server appends the message to the recipient's `inbox/<identity>.log`, pushes it live if the recipient is connected, and persists a per-message record so `reply-all` can reconstruct the recipient set later.

```
                      ┌──────────────────────────────────────────┐
                      │              broker server               │
                      │    ~/.mcp-broker/broker.sock (unix)      │
                      │    inbox/, outbox/, cursors/,            │
                      │    identities.json, messages/            │
                      └──────────────┬───────────────────────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       │                             │                             │
   Claude A                      Claude B                       Human
  (projectA-server)         (@myorg/projectA)             (user / human)
   `broker send`              `broker send`                broker server REPL
   `broker follow`            `broker follow`              who / send / read
   `broker history`           `broker history`             emit-messages on
```

### Roles

The DM model has no room/membership concept. Roles are conventions on top of identities, plus a small server-enforced reservation:

- **User (`user`).** The default identity inside `broker server`. The human running the server interacts with the broker through the in-process REPL — sending DMs, broadcasting, reading their inbox. No token required.
- **Orchestrator (`@orchestrator/<scope>`).** A namespaced coordinator identity. Multiple coordinators can coexist on one host (one per scope, e.g. `@orchestrator/myorg`, `@orchestrator/team-frontend`). The name is a convention, not an authentication boundary — the broker does not verify identity claims for any non-`BROADCAST` identity. Agents that load the broker skill weight DMs by sender identity per the authority hierarchy in `skills/broker/docs/authority.md`.
- **Individual agents.** Each Claude Code instance derives its identity from its workspace: the nearest `package.json` `name`, falling back to `<org>/<repo>` from `git remote origin`. The agent calls `broker whoami` to see what identity it will use; senders compute the same string to address it. Agents can also pin a workspace's identity explicitly with `broker init` (writes `.broker/config.json`).
- **`human` and `BROADCAST`.** `human` is a conventional reserved identity for direct human-as-DM-recipient flows (no longer token-gated). `BROADCAST` is permanently reserved as the fan-out pseudo-recipient and cannot be claimed.

Agents loading the broker skill apply an authority hierarchy when handling conflicting DMs: `user` > `@orchestrator/<your-scope>` > peer agents. See `skills/broker/docs/authority.md` for the full rule.

### Quick start

The fastest path is to let Claude do the setup. Once the plugin is installed, ask Claude:

> "check broker setup"

This runs the broker health check (`skills/broker/docs/health-check.md`) — a 5-point diagnostic of `~/.local/bin` on `$PATH`, the `broker` symlink, server reachability, the `Bash(broker:*)` permission, and version drift between the running broker and the latest cached plugin. Three of the fixes (symlink, permission, version match) Claude can apply for you with your confirmation; PATH and starting the server are user actions.

If you'd rather wire it up by hand:

```bash
# 1. Symlink the CLI onto your $PATH.
ln -s /path/to/skill-cefailures/scripts/broker_cli.py ~/.local/bin/broker

# 2. Start the server in a terminal — drops you into an interactive REPL.
broker server
#   Broker server listening on /Users/you/.mcp-broker/broker.sock
#   Broker REPL — connected as 'user'. Type 'help' for commands.
#   broker>

# 3. Add `Bash(broker:*)` to your Claude Code allowedTools so agents
#    can call the broker without permission prompts.
```

### Usage from the human's perspective

While `broker server` is running, the REPL gives you a small set of DM-aware commands:

```
broker> who
  alice
  projectA-server
  user (you)

broker> send projectA-server please publish v1.2.3
  sent msg-7f3a91

broker> broadcast pausing publishes — npm registry is down
  broadcast msg-b12c04 to 4 identity(s)

broker> read
  2026-04-30T18:21:09Z [projectA-server] READY: shared v1.2.3 published
  2026-04-30T18:23:44Z [@myorg_projectB → you, projectA-server] QUESTION: who owns the migration?

broker> emit-messages on
  emit-messages: on
# every routed message now also prints inline as `[audit] <line>`

broker> help
broker> exit
```

You can also use the same one-shot CLI agents use, from any other terminal — handy for scripts:

```bash
broker send --to projectA-server "READY: shared v1.2.3 published"
broker history --since 2026-04-30T00:00:00Z
broker follow --idle-timeout 60
```

### Usage from an AI agent's perspective

Each agent has the broker skill loaded (see `skills/broker/SKILL.md`), which defines a tight set of patterns. The canonical loop is "send a message, then block on your inbox until a reply arrives or the conversation goes quiet":

```bash
# Agent inside the projectA-server workspace
broker whoami
# projectA-server  (from /Users/you/code/projectA-server)

broker send --to "@myorg/projectA" "QUESTION: which schema version for v1.3?"
# msg-4ab12c

broker follow --idle-timeout 120
# 2026-04-30T18:30:01Z [@myorg_projectA] DECISION: stick with v2 schema
```

Multi-party threads use `reply-all` against a captured message ID — no recipient list to retype:

```bash
MID=$(broker send --to "@myorg/projectA,@myorg/projectB" "QUESTION: validate(schema) or validate(obj)?")
broker follow --idle-timeout 180
broker reply-all --to-message "$MID" "DECISION: validate(schema) wins."
```

An `@orchestrator/<scope>` does the same thing in reverse: it dispatches work, then watches its inbox for status updates from every agent it spawned. A single `broker follow` on the orchestrator's identity captures every reply, every broadcast, and every reply-all that includes it — no per-room follow, no fan-in bookkeeping:

```bash
broker server   # in an orchestrator terminal, with --identity @orchestrator/<scope>

broker> emit-messages on   # tail every routed message in real time
broker> send projectA-server "TASK: cut release branch for v1.3"
broker> send "@myorg/projectA" "TASK: bump shared to v1.2.3"
# replies stream back into the same REPL inbox.
```

### CLI reference

| Command | Description |
|---------|-------------|
| `broker server` | Start the socket server with an interactive DM REPL |
| `broker whoami` | Print the identity derived from the current cwd |
| `broker send --to a,b "<text>"` | DM one or more identities |
| `broker broadcast "<text>"` | Fan out to every registered identity |
| `broker reply-all --to-message MID "<text>"` | Reply to every recipient of a prior DM, excluding self |
| `broker read` | Drain new inbox lines and advance the cursor |
| `broker history [--from X] [--since ISO] [--sent]` | Read inbox (or outbox) without advancing the cursor |
| `broker follow [--idle-timeout N]` | Drain backlog + tail new inbox lines, exit on idle |
| `broker clients` | List identities currently connected to the broker |

For full pattern and troubleshooting docs, see `skills/broker/SKILL.md` and the files in `skills/broker/docs/`.

## How Skills Work

When Claude Code invokes a library skill:

1. **SKILL.md** is loaded — gives Claude an overview, when-to-use triggers, a routing table of reference docs, and key patterns
2. Claude **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
