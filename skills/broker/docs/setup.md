# Broker Setup

## 1. Install the CLI

Create a symlink so `broker` is available in your `$PATH`. Prefer a user-owned directory that's already on your PATH — `~/.local/bin` is a good default and avoids `sudo`:

```bash
mkdir -p ~/.local/bin
ln -s /path/to/skill-cefailures/scripts/broker_cli.py ~/.local/bin/broker
```

If `~/.local/bin` isn't on your PATH yet, add it to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Other user-writable options (pick whichever is already on your PATH): `/opt/homebrew/bin` on Apple Silicon Homebrew installs, or any personal `bin` directory.

`/usr/local/bin` also works but is typically owned by `root`, so it requires `sudo ln -s …`.

Alternatively, add the scripts directory itself to your PATH:

```bash
export PATH="/path/to/skill-cefailures/scripts:$PATH"
```

## 2. Start the broker server

The broker server must be running before agents can connect:

```bash
broker server
```

This starts the Unix domain socket server at `~/.mcp-broker/broker.sock`. Inboxes, outboxes, cursors, and the identity registry all live under `~/.mcp-broker/` (see "Storage layout" below).

## 3. Configure Claude Code permissions

Add `Bash(broker:*)` to your allowedTools so agents can call the broker without permission prompts. In your Claude Code settings or project `CLAUDE.md`:

```
allowedTools:
  - Bash(broker:*)
```

## 4. Install the skill

### As a plugin (recommended)

```
/plugin marketplace add brocef/skill-cefailures
/plugin install skill-cefailures
```

### Local development

```bash
claude --plugin-dir /path/to/skill-cefailures
```

## 5. Tell agents to use the broker

Once the server is running and the skill is installed, tell agents something like:

```
You have a broker CLI. Check your identity with `broker whoami`; catch up with
`broker history`; DM other agents with `broker send --to <identity>`; and when
you're waiting for a reply, use `broker follow` (it blocks and streams new
messages). See the broker skill docs for patterns.
```

Agents will follow the patterns in `patterns.md` to wait for replies without writing polling loops.

## Reserved identities

`orchestrator`, `human`, and `BROADCAST` are reserved at the server level:

- **`BROADCAST`** — never claimable. It's the pseudo-recipient on `broker broadcast` fan-outs.
- **`orchestrator`** and **`human`** — claimable only by processes that present a matching token. Create the token file before connecting:

  ```bash
  mkdir -p ~/.mcp-broker/tokens
  echo "anything-non-empty" > ~/.mcp-broker/tokens/orchestrator.token
  echo "anything-non-empty" > ~/.mcp-broker/tokens/human.token
  ```

  Note: the CLI does not yet plumb the token to the server on connect — this is tracked follow-up work. In practice, most agents use their cwd-derived identity and leave reserved identities for humans and orchestration processes.

## Multi-workspace note

There is one `orchestrator` per broker instance (per host). If you run multiple workspaces that each need a distinct coordinator, use scoped identities instead of the reserved one:

```
orchestrator:proposit-app
orchestrator:proposit-mobile
```

These are ordinary identities — no token file required — so each workspace can have its own without collision. This is a documented limitation, not a bug.

## Storage layout

Everything the broker persists lives under `~/.mcp-broker/`:

- `inbox/<encoded-identity>.log` — DMs received (one display-format line per message).
- `outbox/<encoded-identity>.log` — DMs sent, same shape.
- `cursors/<encoded-identity>.cursor` — byte offset into the inbox log, advanced by `broker read`.
- `identities.json` — registry of known identities (first/last seen, canonical form).
- `messages/<message-id>.json` — raw records used by `reply-all` to recover recipient sets.
- `tokens/<identity>.token` — per-host tokens for reserved identities.
- `conversations/` — legacy room state (deprecated, still present for backward compat).

Identity encoding: `/` becomes `_` in filenames (`@proposit/shared` → `@proposit_shared.log`).
