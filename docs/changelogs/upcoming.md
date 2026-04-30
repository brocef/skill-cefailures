# Upcoming

## Added
- Broker reserved-identity tokens are now end-to-end. The CLI accepts `--token <value>` (and the `BROKER_TOKEN` env var) on every subcommand and forwards it to the server on connect. Lets `orchestrator` / `human` actually claim their identities — previously the server enforced the token file but no client could send a token.
- `broker server` REPL is rewritten for the DM model: `who` lists connected identities, `send <id[,id...]> <text>` and `broadcast <text>` send messages, `read` / `history` drain or browse the inbox, and `emit-messages on|off` toggles a live audit tail of every routed message.
- `broker clients` subcommand lists identities currently connected to the broker.
- `BrokerServer.audit_hook` callback fires once per routed message so external observers (the REPL, future log shipping) can tail traffic without polling.
- README has a top-level "Message Broker" section covering architecture, the user/orchestrator/agent role model, and usage examples from both the human's and an AI agent's perspective.

## Changed
- **Breaking:** the room-based broker API and CLI surface are gone. Removed: `create_conversation`, `join_conversation`, `leave_conversation`, `close_conversation`, `send_message`, `history`, `list_conversations`, `list_members` (server + client + CLI). Subcommands `create`, `join`, `leave`, `close`, `members`, `list`, and `repl` no longer exist.
- **Breaking:** `BrokerServer` constructor parameter renamed from `storage_dir` (the conversations subdir) to `root_dir` (the broker root, e.g. `~/.mcp-broker`). The `MCP_BROKER_STORAGE` env var is replaced by `MCP_BROKER_ROOT`. CLI flag `--storage-dir` is renamed `--root-dir`.
- The `~/.mcp-broker/conversations/` directory is no longer used. Existing data there is dead and can be deleted.
- `broker_client.py` no longer exposes room methods or buffers room pushes; the API is `send_dm`, `broadcast`, `reply_all`, `history_inbox`, `read_inbox`, `list_clients`.

## Fixed
- Broker server no longer raises `Unhandled exception in client_connected_cb` when a client tries to connect as a reserved identity without a matching token. The rejection is returned to the client as a structured error response, and the BrokerClient surfaces it as a `ValueError` from `connect()`.
