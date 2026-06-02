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

Skills are available as `/skill-cefailures:<skill-name>` (e.g. `/skill-cefailures:ieee`).

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

### Via symlinks (legacy)

```bash
pip install -r requirements.txt

# Install a single skill
python scripts/install_skill.py knex

# Install a single skill for Codex
python scripts/install_skill.py --agent codex knex

# Install all skills for both Claude Code and Codex
python scripts/install_skill.py --agent all --all

# Install all skills
python scripts/install_skill.py --all

# List available skills
python scripts/install_skill.py --list

# Uninstall a skill
python scripts/install_skill.py --remove knex

# Uninstall all skills
python scripts/install_skill.py --remove-all
```

By default, this creates symlinks from `~/.claude/skills/<name>` to the skills in this repo. Use `--agent codex` to target `~/.codex/skills/<name>`, or `--agent all` to install both.

## Creating a new skill

```bash
pip install -r requirements.txt

# Using OpenAI (default — requires OPENAI_API_KEY)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md"

# Using Anthropic SDK (requires ANTHROPIC_API_KEY)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md" --backend sdk

# Using the local Claude CLI (no API key needed; requires Claude Code installed)
python scripts/create_skill.py --name knex --url "https://example.com/knex-docs.md" --backend cli
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
  broker/                     # /skill-cefailures:broker:* commands
  documentation-sync/         # /skill-cefailures:documentation-sync:* commands
  permissions-auditor/        # /skill-cefailures:permissions-auditor:* commands
  process-inbox.md            # /skill-cefailures:process-inbox
  process-inbox-initiative.md # /skill-cefailures:process-inbox-initiative (orchestrator-only)
skills/                       # Eight skills, one directory each
  brain-style/
  broker/
  capabilities-sdlc/
  documentation-sync/
  elkjs/
  ieee/
  knex/
  typebox/
  <name>/
    SKILL.md                  # Routing layer (loaded on invocation)
    docs/
      <topic>.md              # Detailed reference (read on demand)
plugins/
  skill-cefailures -> ..      # Codex marketplace pointer to the repo-root plugin
scripts/
  create_skill.py             # Generate skill from URL
  install_skill.py            # Symlink skills to ~/.claude/skills/ and/or ~/.codex/skills/
  analyze_permissions.py      # Analyze permission request logs
  apply_permissions.py        # Apply curated permission lists to settings.json
  log-permission-requests.sh  # Permission logging hook script
  broker_server.py            # Broker server: state, routing, persistence
  broker_client.py            # Async socket client for the broker
  broker_cli.py               # Broker CLI: server, REPL, one-shot subcommands
  broker_constants.py         # Shared protocol constants
  broker_format.py            # Message format helpers
  broker_identity.py          # Identity resolution (workspace → identity)
  broker_storage.py           # Persistence (inbox/outbox/cursors)
tests/                        # pytest suite
docs/
  release-notes/              # Per-version user-facing notes (vX.Y.Z.md + upcoming.md)
  changelogs/                 # Per-version developer changelogs
  plans/                      # Design and implementation documents
AGENTS.md                     # Project instructions for Codex and compatible agents
CLAUDE.md                     # Symlink to AGENTS.md for Claude Code compatibility
requirements.txt
```

## Skills

| Skill | Purpose |
|-------|---------|
| `brain-style` | Code style preferences across TypeScript naming and types. |
| `broker` | Namespace for the broker DM/inbox CLI's shared reference docs (rules, signals, authority). All workflows are slash commands — see [Message Broker](#message-broker) below. |
| `capabilities-sdlc` | User-capability documentation conventions, planning gate, and contradiction-detection rule for Proposit-style `capabilities.md` files. |
| `documentation-sync` | Evaluate trigger-based documentation update rules from a project's `CLAUDE.md` after code changes. |
| `elkjs` | Automatic graph layout via the elkjs JavaScript port of the Eclipse Layout Kernel. |
| `ieee` | IEEE editorial style, citation/reference formatting, mathematical notation, and TypeBox schema derivation for IEEE reference types. |
| `knex` | Knex.js setup, configuration, connection behavior, and SQL dialect handling. |
| `typebox` | Runtime type system with JSON Schema definitions that infer to TypeScript types. |

## Slash Commands

This plugin ships slash commands under `commands/` (registered via `plugin.json`). Commands are for workflows that are *purely* user-explicit — they replace the auto-trigger metadata of skills, which keeps skill descriptions narrow and saves session context.

| Command | Purpose |
|---------|---------|
| `/skill-cefailures:brain-style:review` | Architecture review of a file/function/class against decomposition, file-size, and redundancy guidelines. |
| `/skill-cefailures:brain-style:claude-md` | Review or author a project's `CLAUDE.md` against the minimal-routing principle and required-sections checklist. |
| `/skill-cefailures:documentation-sync:setup` | Walk a project through adding a `## Documentation Sync` section to its `CLAUDE.md` and create any tracked files that don't yet exist. |
| `/skill-cefailures:documentation-sync:cut-version` | Cut a new version: choose the bump size, update every version-bearing file, rotate `upcoming.md` to `v{version}.md`, commit, and tag. |
| `/skill-cefailures:process-inbox` | Pick a request document from `docs/inbox/` (loose file or folder bundle), read it plus any supporting artifacts, route it via superpowers if installed, then move the source into `docs/inbox/.archive/`. |
| `/skill-cefailures:process-inbox-initiative` | Orchestrator-only. Process an org-root inbox doc as a multi-repo initiative: capabilities-first, then one durable agent per affected repo coordinates research subagents, spec review subagents, implementation, and per-repo integration. Builds on `process-inbox`. |
| `/skill-cefailures:permissions-auditor:install` | Install the permission-logging hook so future permission prompts are captured for later triage. |
| `/skill-cefailures:permissions-auditor:analyze` | Analyze logged permission requests, present recurring patterns, and triage them into allow/deny/manual-review rules. |
| `/skill-cefailures:broker:setup` | First-time broker setup: symlink the CLI, start the server, confirm identity, register the `Bash(broker:*)` permission. |
| `/skill-cefailures:broker:mode` | Enter Broker Mode — the foreground read-execute-respond loop, one iteration per inbox batch. |
| `/skill-cefailures:broker:send` | Send a broker DM, broadcast, or reply-all. |
| `/skill-cefailures:broker:read` | Drain the inbox (`broker recv`) or peek at history (`broker history`). |
| `/skill-cefailures:broker:doctor` | Diagnose broker setup — a 5-point health check covering `$PATH`, CLI symlink, server reachability, permission, and version drift. |

## Message Broker

A direct-message bus that lets Claude Code agents (and a human) talk to each other in real time. Every participant has a persistent identity and a per-identity inbox on disk, so messages survive restarts and can be addressed without any kind of conversation/room setup.

Broker commands are intentionally opt-in. The `broker` skill is reduced to a namespace stub — its only purpose is to host the shared reference docs under `skills/broker/docs/` that the broker commands read. Agents should load broker instructions only when the user runs one of the `/skill-cefailures:broker:*` commands.

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
   `broker recv`              `broker recv`                who / send / read
   `broker history`           `broker history`             emit-messages on
```

### Roles

The DM model has no room/membership concept. Roles are conventions on top of identities, plus a small server-enforced reservation:

- **User (`user`).** The default identity inside `broker server`. The human running the server interacts with the broker through the in-process REPL — sending DMs, broadcasting, reading their inbox. No token required.
- **Orchestrator (`@orchestrator/<scope>`).** A namespaced coordinator identity. Multiple coordinators can coexist on one host (one per scope, e.g. `@orchestrator/myorg`, `@orchestrator/team-frontend`). The name is a convention, not an authentication boundary — the broker does not verify identity claims for any non-`BROADCAST` identity. Agents running broker commands weight DMs by sender identity per the authority hierarchy in `skills/broker/docs/authority.md`.
- **Individual agents.** Each Claude Code instance derives its identity from its workspace: the nearest `package.json` `name`, falling back to `<org>/<repo>` from `git remote origin`. The agent calls `broker whoami` to see what identity it will use; senders compute the same string to address it. Agents can also pin a workspace's identity explicitly with `broker init` (writes `.broker/config.json`).
- **`human` and `BROADCAST`.** `human` is a conventional reserved identity for direct human-as-DM-recipient flows (no longer token-gated). `BROADCAST` is permanently reserved as the fan-out pseudo-recipient and cannot be claimed.

Agents running broker commands apply an authority hierarchy when handling conflicting DMs: `user` > `@orchestrator/<your-scope>` > peer agents. See `skills/broker/docs/authority.md` for the full rule.

### Quick start

The fastest path is to let Claude do the setup. Once the plugin is installed, run either:

- `/skill-cefailures:broker:setup` — first-time install walkthrough.
- `/skill-cefailures:broker:doctor` — verify an existing install via a 5-point health check covering `~/.local/bin` on `$PATH`, the `broker` symlink, server reachability, the `Bash(broker:*)` permission, and version drift between the running broker and the latest cached plugin. Three of the fixes (symlink, permission, version match) Claude can apply for you with your confirmation; PATH and starting the server are user actions.

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
broker recv --burst-window 5
```

### Usage from an AI agent's perspective

When the user explicitly asks for broker coordination, they run one of the `/skill-cefailures:broker:*` commands. The canonical waiting pattern is **Broker Mode** — entered via `/skill-cefailures:broker:mode` — which runs an explicit foreground read-execute-respond loop, one iteration per inbox batch. Outside Broker Mode, agents use `broker recv` directly for a "send-and-wait" one-shot:

```bash
# Agent inside the projectA-server workspace
broker whoami
# projectA-server  (from /Users/you/code/projectA-server)

broker send --to "@myorg/projectA" "QUESTION: which schema version for v1.3?"
# msg-4ab12c

broker recv --burst-window 5
# 2026-04-30T18:30:01Z [@myorg_projectA] DECISION: stick with v2 schema
```

Multi-party threads use `reply-all` against a captured message ID — no recipient list to retype:

```bash
MID=$(broker send --to "@myorg/projectA,@myorg/projectB" "QUESTION: validate(schema) or validate(obj)?")
broker recv --burst-window 5
broker reply-all --to-message "$MID" "DECISION: validate(schema) wins."
```

An `@orchestrator/<scope>` does the same thing in reverse: it dispatches work, then watches its inbox for status updates from every agent it spawned. Run `/skill-cefailures:broker:mode` and the orchestrator picks up every reply, broadcast, and reply-all that includes it — one batch per loop iteration, no per-room follow, no fan-in bookkeeping:

```bash
broker server --identity "@orchestrator/<scope>"   # in an orchestrator terminal

broker> emit-messages on   # tail every routed message in real time
broker> send projectA-server "TASK: cut release branch for v1.3"
broker> send "@myorg/projectA" "TASK: bump shared to v1.2.3"
# replies stream back into the same REPL inbox.
```

### CLI reference

| Command | Description |
|---------|-------------|
| `broker server [--identity ID]` | Start the socket server with an interactive DM REPL |
| `broker whoami` | Print the identity derived from the current cwd |
| `broker init [--identity ID] [--force]` | Pin a workspace's identity by writing `.broker/config.json` |
| `broker send --to a,b "<text>"` | DM one or more identities |
| `broker broadcast "<text>"` | Fan out to every registered identity |
| `broker reply-all --to-message MID "<text>"` | Reply to every recipient of a prior DM, excluding self |
| `broker read [--show-ids]` | Drain new inbox lines and advance the cursor |
| `broker history [--from X] [--since ISO] [--sent] [--show-ids]` | Read inbox (or outbox) without advancing the cursor |
| `broker recv [--timeout N] [--burst-window M] [--show-ids]` | Receive the next batch of inbox messages (used inside Broker Mode) |
| `broker clients` | List identities currently connected to the broker |
| `broker --version` | Print the broker version (also `-V`) |

The canonical agent-side pattern is `/skill-cefailures:broker:mode`, which runs the read-execute-respond loop using `broker recv` under the hood. The Broker Mode procedure lives in `skills/broker/docs/patterns.md`.

For full pattern and troubleshooting reference, see the files in `skills/broker/docs/` (`patterns.md`, `critical-rules.md`, `signals.md`, `authority.md`, `troubleshooting.md`, `usage.md`).

## How Skills Work

When an agent invokes a library skill:

1. **SKILL.md** is loaded — gives the agent a brief overview and a routing table to reference docs in `docs/`. The frontmatter `description` field acts as the skill's invocation criteria.
2. The agent **reads specific docs/** files based on the current task — only what's needed
3. Reference docs contain full API details, examples, and troubleshooting
