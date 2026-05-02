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

`broker recv` requires the server to be running — without it, `recv` exits immediately with `Cannot connect to broker at …`. All other subcommands (`send`, `history`, `read`, `whoami`) operate on the on-disk files and do not need the server.

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
you're waiting for inbound work, use `broker recv` inside Broker Mode (it
blocks for the next batch and exits when the batch is delivered). See the
broker skill docs for patterns.
```

Agents will follow the patterns in `patterns.md` to wait for replies without writing polling loops.

## Reserved identities

`@orchestrator/<scope>` and `human` are conventional identity names with elevated authority per the skill's authority hierarchy. They are NOT authenticated — any process on the host can claim them. See `docs/authority.md`.

`BROADCAST` is permanently reserved as the broadcast pseudo-recipient and cannot be claimed.

## Multi-workspace note

Each workspace can have its own orchestrator by picking a different `<scope>`:

```
@orchestrator/projectA
@orchestrator/projectB-mobile
```

There's no shared per-host singleton; multiple `broker server --identity @orchestrator/<scope>` processes can coexist (one per scope).

## Pinning a workspace identity

By default, the broker derives your identity from cwd (nearest `package.json` `name`, then `<org>/<repo>` from git remote). To pin a fixed identity for a workspace, run `broker init` inside that directory:

```
broker init                         # uses cwd-derived identity
broker init --identity @myorg/projectA   # explicit
broker init --identity alice --force     # overwrite an existing pinned identity
```

This writes `.broker/config.json` in the **current** directory only — `broker init` does not walk up to find an existing config. If you want to update a parent workspace's pin, edit its `.broker/config.json` directly. Subsequent `broker` invocations from anywhere inside the pinned dir will use the pinned identity (the read-side walk-up search finds the nearest `.broker/config.json`).

**Monorepo precedence:** if you nest projects under an orchestrator that pins itself with `.broker/config.json` (e.g. `/org/.broker/config.json` for `@org`, with `/org/projectA/package.json` for `@org/projectA`), the project's `package.json` wins from inside `/org/projectA` because it's closer to cwd. The orchestrator root still resolves to `@org` because there's no `package.json` between cwd and the config. To override a project's `package.json`, drop a `.broker/config.json` in the project directory (same-dir ties go to the config file).

`.broker/config.json` is a small JSON file:

```json
{
  "identity": "@myorg/projectA"
}
```

Add `.broker/` to your project's `.gitignore` if you don't want to commit the pinned identity.

## Storage layout

Everything the broker persists lives under `~/.mcp-broker/`:

- `inbox/<encoded-identity>.log` — DMs received (one display-format line per message).
- `outbox/<encoded-identity>.log` — DMs sent, same shape.
- `cursors/<encoded-identity>.cursor` — byte offset into the inbox log, advanced by `broker read`.
- `identities.json` — registry of known identities (first/last seen, canonical form).
- `messages/<message-id>.json` — raw records used by `reply-all` to recover recipient sets.

Identity encoding: `/` becomes `_` in filenames (`@myorg/projectA` → `@myorg_projectA.log`).
