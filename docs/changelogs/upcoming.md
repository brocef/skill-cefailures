# Upcoming

## Added
- Namespaced orchestrator identities: `@orchestrator/<scope>` replaces the v1.4.0 singleton `orchestrator`. Multiple orchestrators can coexist on one broker host, each with its own token file at `~/.mcp-broker/tokens/@orchestrator_<scope>.token`. Scope must match `[A-Za-z0-9._-]{1,64}`.
- Authority hierarchy convention in the broker skill: `SKILL.md` adds Critical rule #5 ("Weigh DMs by sender authority") pointing at a new `skills/broker/docs/authority.md` with the full prose. Order is `user` > `@orchestrator/<your-scope>` > peer agents; on conflict, relay upstream.
- `.broker/config.json` per-cwd identity pinning. Walk-up lookup (stops at `$HOME`) sits between the `--identity` flag and cwd-derivation; symlinks resolve normally; malformed JSON warns and falls through. New `broker init [--identity X] [--force]` subcommand creates the file in the current directory.
- `BROKER_IDENTITY` env var is honored as a fallback when `--identity` is omitted.
- `--show-ids` flag on `broker read` / `broker history` / `broker follow`. Prefixes each emitted line with the message ID (10-char column + 2-space gutter), letting recipients run `reply-all --to-message <MID>` without rummaging through `send` stdout. Legacy lines (pre-v1.5.0) render an em-dash placeholder.
- CLI-level `--identity` validation rejects `@orchestrator`, `@orchestrator/`, and any `@orchestrator/<scope>` whose scope contains invalid characters or exceeds 64 chars. The check fires at parse time, before connect, so typos surface as a clear argparse error rather than silently connecting in peer mode.
- `ORCHESTRATOR_RE` is exposed as a public symbol on `broker_constants` (was previously `_ORCHESTRATOR_RE`) so the CLI validator and other consumers can use it without reaching for a private name.

## Changed
- **Breaking:** the bare `orchestrator` identity is no longer reserved. It now connects as a peer (no token required). Token files at `~/.mcp-broker/tokens/orchestrator.token` are inert.
- **Breaking:** inbox and outbox log files now write `<MID>\t<line>` per entry. Existing files (pre-v1.5.0) remain readable — `split_mid_prefix()` detects them by the leading character (digit = legacy timestamp, `m` = MID prefix).
- `BrokerServer._read_token` now passes the identity through `encode_identity()` so namespaced reserved identities resolve to the correct token file path.
- `_handle_history_inbox` strips MID prefix before passing each line to `parse_message` for `--from`/`--since` filtering (downstream of the wire-format change).

## Removed
- `RESERVED_IDENTITIES` no longer contains the bare string `"orchestrator"`. The frozenset now holds `{"human", "BROADCAST"}` only; the `@orchestrator/<scope>` pattern is matched separately by the new `is_reserved()` predicate.
