# Upcoming — broker namespacing, authority hierarchy, and ergonomic polish

## Broker

This release builds on v1.4.0's DM-only refactor with four pieces: namespaced orchestrators, an authority hierarchy convention, per-workspace identity pinning, and an opt-in MID column on read.

### Namespaced orchestrators

The single reserved `orchestrator` identity is replaced by `@orchestrator/<scope>` — multiple coordinators per host, each with its own token file. Scope must match `[A-Za-z0-9._-]{1,64}`.

```bash
mkdir -p ~/.mcp-broker/tokens
echo "secret-value" > ~/.mcp-broker/tokens/@orchestrator_myorg.token
broker server --identity @orchestrator/myorg --token secret-value
```

CLI argparse rejects malformed orchestrator names (`@orchestrator`, `@orchestrator/`, `@orchestrator/with spaces`) at parse time so typos surface clearly instead of silently downgrading to peer mode.

### Authority hierarchy

`skills/broker/SKILL.md` adds Critical rule #5: agents should weigh DMs by sender authority (`user` > `@orchestrator/<your-scope>` > peer agents) and relay conflicts upstream rather than silently complying. Full prose lives in `skills/broker/docs/authority.md`.

The hierarchy is enforceable for the top two tiers (token-gated) and conventional for peers (unauthenticated by design — local-only threat model).

### `.broker/config.json` and `broker init`

Pin a workspace's identity once instead of passing `--identity` everywhere:

```bash
cd ~/code/projectA
broker init --identity @myorg/projectA   # writes .broker/config.json
broker send --to bob "hello"             # uses @myorg/projectA without --identity
```

Walk-up lookup stops at `$HOME` so a stray config in `/` doesn't leak into every workspace. Malformed JSON or missing/invalid `identity` field warns on stderr and falls through to the cwd-derivation rule. `BROKER_IDENTITY` env var is honored between the explicit flag and the config file.

### `--show-ids`

`broker read --show-ids`, `broker history --show-ids`, and `broker follow --show-ids` prepend the message ID to each line:

```
$ broker read --show-ids
msg-7f3a91  2026-04-30T18:21:09Z [alice] hello bob
msg-c042bf  2026-04-30T18:23:44Z [carol → you, bob] question for the team
—           2026-04-29T11:02:11Z [legacy-sender] pre-v1.5.0 message with no MID column
```

Default off; the existing format is unchanged. Legacy inbox/outbox lines (pre-v1.5.0, no MID column on disk) render an em-dash placeholder.

## Breaking changes

- **Bare `orchestrator` identity is no longer reserved.** Connections as `orchestrator` succeed without a token (peer mode); `~/.mcp-broker/tokens/orchestrator.token` is inert. Migrate to `@orchestrator/<scope>`.
- **Inbox/outbox wire format changes.** Lines now have a `<MID>\t` prefix. Existing pre-v1.5.0 files remain readable.
- **Anything that imported `RESERVED_IDENTITIES` and expected `"orchestrator"` to be in it** must switch to `from broker_constants import is_reserved` and call `is_reserved(identity)`.
- **`MCP_BROKER_STORAGE` is unchanged in v1.5.0** (the v1.4.0 rename to `MCP_BROKER_ROOT` is what's in effect). Mentioning here only because the v1.4.0 release notes covered it; no further change in v1.5.0.

If you were running v1.4.0 with `--identity orchestrator --token X`, do this once:

```bash
mv ~/.mcp-broker/tokens/orchestrator.token ~/.mcp-broker/tokens/@orchestrator_default.token
broker server --identity @orchestrator/default --token X
```
