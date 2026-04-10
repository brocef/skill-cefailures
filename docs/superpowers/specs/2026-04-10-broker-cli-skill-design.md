# Broker CLI Skill — Design Spec

Replace the MCP server interface with CLI subcommands and a Claude Code skill. Agents use the `broker` command via Bash instead of MCP tools. The socket server, client, and persistence layer are unchanged.

## Architecture

```
Agent A (Claude Code)                Agent B (Claude Code)
  | Bash("broker send ...")            | Bash("broker read ...")
  v                                    v
broker_cli.py send                  broker_cli.py read
  | connect -> request -> disconnect   | connect -> request -> disconnect
  +----------------+------------------+
                   | Unix domain socket
                   v
         broker_cli.py server
         (socket server + human REPL)
         persists to ~/.mcp-broker/conversations/
```

- Each subcommand connects to the socket, performs one operation, prints JSON to stdout, and exits
- One-shot subcommands use `BrokerClient` directly: connect, make one async call, close. The listener task and push buffer are unnecessary overhead for one-shot use but keep the code DRY — no separate lightweight client.
- The socket server and human REPL remain unchanged
- `broker_server.py` and `broker_client.py` are untouched
- A new `skills/broker/` skill teaches agents how to use the CLI

## CLI Subcommands

All subcommands except `server` and `repl` connect to the socket, do one thing, print JSON to stdout, and exit. `--identity` is required for agent-facing subcommands. For `server` and `repl`, `--identity` defaults to `"user"`. `--socket` is optional everywhere (defaults to `~/.mcp-broker/broker.sock`).

### Server and REPL

```
broker server [--identity USER] [--socket PATH] [--storage-dir PATH]
```

Start the socket server and human REPL. Identity defaults to `"user"`. Storage directory defaults to `~/.mcp-broker/conversations`.

```
broker repl [--identity NAME] [--socket PATH]
```

Connect to a running server as a client REPL.

### Agent-facing subcommands

All of these require `--identity NAME` and output JSON to stdout. `--status` on `list` uses `choices=["open", "closed"]` for validation.

CLI subcommand to server protocol mapping:

| CLI subcommand | Server request type |
|---------------|-------------------|
| `create` | `create_conversation` |
| `send` | `send_message` |
| `read` | `history` |
| `list` | `list_conversations` |
| `members` | `list_members` |
| `join` | `join_conversation` |
| `leave` | `leave_conversation` |
| `close` | `close_conversation` |

```
broker create --identity NAME TOPIC [--content "seed message"]
```
Create a conversation. Output: `{"conversation_id": "abc123", "topic": "...", "created_by": "..."}`

```
broker send --identity NAME CONVERSATION_ID CONTENT
```
Send a message (auto-joins). Output: `{"message_id": "msg-...", "conversation_id": "...", "sender": "..."}`

```
broker read --identity NAME CONVERSATION_ID
```
Read new messages (advances cursor). Does not auto-join — reading is not participating. Messages include system messages (join/leave events) with `"sender": "system"`. Output: `{"conversation_id": "...", "messages": [{"id": "...", "sender": "...", "content": "...", "timestamp": "..."}]}`

```
broker list --identity NAME [--status open|closed]
```
List conversations. Output: `{"conversations": [{"id": "...", "topic": "...", "status": "...", "created_by": "...", "message_count": N, "unread_count": N}]}`

```
broker members --identity NAME CONVERSATION_ID
```
List members. Output: `{"conversation_id": "...", "members": ["..."]}`

```
broker join --identity NAME CONVERSATION_ID
```
Join a conversation. Output: `{"conversation_id": "...", "status": "joined"}`

```
broker leave --identity NAME CONVERSATION_ID
```
Leave a conversation. Output: `{"conversation_id": "...", "status": "left"}`

```
broker close --identity NAME CONVERSATION_ID
```
Close a conversation (read-only). Output: `{"conversation_id": "...", "status": "closed"}`

### Error handling

Errors print JSON to stderr and exit with code 1:
```json
{"error": "Conversation 'xyz' not found"}
```

Connection failures (server not running) also use JSON to stderr and exit 1:
```json
{"error": "Cannot connect to broker at ~/.mcp-broker/broker.sock. Is the broker server running?"}
```

## Skill Structure

### `skills/broker/SKILL.md`

The routing layer, loaded when the skill is invoked.

Description triggers: collaborating with other agents, coordinating with other Claude Code instances, multi-agent conversations, talking to another agent.

Contents:
- What the broker is (chatroom-like CLI for multi-agent conversations)
- Prerequisite: broker server must be running, `Bash(broker:*)` must be in allowedTools
- The polling pattern: keep calling `broker read --identity <you> <conversation_id>` in a loop until the conversation is closed or you see a stop message, unless the user says otherwise
- Routing table to `docs/usage.md` and `docs/setup.md`
- Quick reference of subcommands

### `skills/broker/docs/usage.md`

Full CLI reference:
- All subcommands with examples and expected JSON output
- Common workflows (create conversation, send messages, poll for responses)
- Error handling (exit codes, error JSON format)

### `skills/broker/docs/setup.md`

Installation instructions:
- Symlink `broker_cli.py` to somewhere in `$PATH` as `broker`
- Start the broker server: `broker server`
- Add `Bash(broker:*)` to allowedTools in Claude Code settings
- How to install the skill (plugin marketplace or `--plugin-dir`)

## Changes

### Modified files

| File | Changes |
|------|---------|
| `scripts/broker_cli.py` | Add argparse subcommands (`create`, `send`, `read`, `list`, `members`, `join`, `leave`, `close`). Refactor `--server` to `server` subcommand, no-flag mode to `repl` subcommand. Each one-shot subcommand connects to socket, sends request, prints JSON, exits. |
| `tests/test_broker_cli.py` | Add tests for each one-shot subcommand: start a server, run subcommand, assert JSON output and exit code. Existing REPL tests stay. |
| `.claude-plugin/plugin.json` | Add `"broker"` to keywords list. |
| `README.md` | Remove MCP server references (install_broker, .mcp.json, MCP tools table). Replace with CLI usage, skill installation, broker subcommand reference. |

### New files

| File | Purpose |
|------|---------|
| `skills/broker/SKILL.md` | Skill routing layer with triggers, polling pattern, quick reference |
| `skills/broker/docs/usage.md` | Full CLI reference with examples and JSON output formats |
| `skills/broker/docs/setup.md` | Installation and configuration instructions |

### Deleted files

| File | Reason |
|------|--------|
| `scripts/mcp_broker.py` | MCP server replaced by CLI subcommands |
| `scripts/install_broker.py` | Wrote `.mcp.json`, no longer needed |
| `tests/test_mcp_broker.py` | Tested MCP tools and ConversationStore |
| `tests/test_install_broker.py` | Tested install/remove functions |

### Unchanged files

| File | Reason |
|------|--------|
| `scripts/broker_server.py` | Socket server, state management, persistence — untouched |
| `scripts/broker_client.py` | Async socket client — untouched |
| `tests/test_broker_server.py` | Server tests — untouched |
| `tests/test_broker_transport.py` | Socket transport tests — untouched |
| `tests/test_broker_client.py` | Client tests — untouched |
| `tests/test_broker_e2e.py` | End-to-end test — untouched |

## Not in scope

- Proactive push notifications to agents (Claude Code doesn't support server-initiated actions)
- Authentication or encryption (local-only, trust is ambient)
- `pyproject.toml` or pip-installable entry points (symlink approach chosen)
- Changes to the socket protocol
