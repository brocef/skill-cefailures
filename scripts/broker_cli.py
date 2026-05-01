#!/usr/bin/env python3
"""CLI for the multi-agent message broker (DM model)."""

import argparse
import asyncio
import json
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


SERVER_HELP = """\
Commands:
  who                       List identities currently connected
  send <identity> <text>    Send a DM to one identity
  send <id1,id2> <text>     Send a DM to multiple identities (comma-separated, no spaces)
  broadcast <text>          Broadcast to every registered identity
  read                      Drain your inbox (advances the cursor)
  history                   Show your inbox without advancing the cursor
  emit-messages on|off      Toggle live tailing of every routed message
  help                      Show this help
  exit                      Quit"""


class ServerREPL:
    """REPL that runs inside the server process, using BrokerServer directly.

    Provides interactive DM operations for the human running `broker server`.
    Supports an optional 'emit-messages' tail of every routed message via the
    server's audit_hook.
    """

    def __init__(self, server: BrokerServer, identity: str) -> None:
        self.server = server
        self.identity = identity
        self._req_counter = 0
        self.server.connect(identity, self._on_push, mode="follow")
        self._emit_messages = False
        # Wire the audit hook so live messages can be tailed.
        self.server.audit_hook = self._audit
        self._lock = threading.Lock()

    def _next_id(self) -> str:
        self._req_counter += 1
        return f"repl-{self._req_counter}"

    def _request(self, msg: dict) -> dict:
        msg["id"] = self._next_id()
        result = self.server.handle_request(self.identity, msg)
        if result["type"] == "error":
            raise ValueError(result["message"])
        return result["data"]

    def _on_push(self, msg: dict) -> None:
        """Inbox messages addressed to the REPL identity print as `<- <line>`."""
        if msg.get("type") == "inbox_message":
            with self._lock:
                print(f"\n<- {msg['line']}", flush=True)

    def _audit(self, line: str) -> None:
        """Tail every routed message when emit-messages is on."""
        if self._emit_messages:
            with self._lock:
                print(f"\n[audit] {line}", flush=True)

    def lobby_loop(self) -> None:
        print(f"Broker REPL — connected as {self.identity!r}. Type 'help' for commands.")
        while True:
            try:
                line = input("broker> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            try:
                if not self._dispatch(line):
                    return
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)

    def _dispatch(self, line: str) -> bool:
        """Run one REPL command. Returns False to exit the loop."""
        parts = line.split(None, 1)
        command = parts[0].lower()

        if command == "exit":
            return False
        if command == "help":
            print(SERVER_HELP)
            return True
        if command == "who":
            data = self._request({"type": "list_clients"})
            live = data.get("live", [])
            offline = data.get("offline", [])
            if not live and not offline:
                print("  (no live followers, no registered identities)")
                return True
            for entry in live:
                marker = " (you)" if entry["identity"] == self.identity else ""
                print(f"  {entry['identity']}       live, since {entry['since']}{marker}")
            for entry in offline:
                last_seen = entry.get("lastSeenAt", "—")
                print(f"  {entry['identity']}       offline, last seen {last_seen}")
            return True
        if command == "send":
            if len(parts) < 2:
                print("Usage: send <identity[,identity...]> <text>", file=sys.stderr)
                return True
            rest = parts[1].split(None, 1)
            if len(rest) < 2:
                print("Usage: send <identity[,identity...]> <text>", file=sys.stderr)
                return True
            recipients = [r.strip() for r in rest[0].split(",") if r.strip()]
            content = rest[1]
            data = self._request({"type": "send_dm", "to": recipients, "content": content})
            print(f"  sent {data['message_id']}")
            return True
        if command == "broadcast":
            if len(parts) < 2:
                print("Usage: broadcast <text>", file=sys.stderr)
                return True
            data = self._request({"type": "send_broadcast", "content": parts[1]})
            print(f"  broadcast {data['message_id']} to {data['recipient_count']} identity(s)")
            return True
        if command == "read":
            data = self._request({"type": "read_inbox"})
            for entry in data["lines"]:
                print(f"  {entry}")
            if not data["lines"]:
                print("  (inbox empty)")
            return True
        if command == "history":
            data = self._request({"type": "history_inbox"})
            for entry in data["lines"]:
                print(f"  {entry}")
            if not data["lines"]:
                print("  (no history)")
            return True
        if command == "emit-messages":
            arg = parts[1].strip().lower() if len(parts) > 1 else ""
            if arg in ("on", "true", "1"):
                self._emit_messages = True
                print("  emit-messages: on")
            elif arg in ("off", "false", "0"):
                self._emit_messages = False
                print("  emit-messages: off")
            elif arg == "":
                state = "on" if self._emit_messages else "off"
                print(f"  emit-messages: {state}")
            else:
                print("Usage: emit-messages [on|off]", file=sys.stderr)
            return True
        print(f"Unknown command: {command}. Type 'help' for options.", file=sys.stderr)
        return True


async def run_server_mode(
    identity: str, root_dir: Path, sock_path: str,
) -> None:
    """Start the socket server and run the REPL."""
    server = BrokerServer(root_dir=root_dir)
    srv = await start_server(server, sock_path)
    print(f"Broker server listening on {sock_path}")

    repl = ServerREPL(server, identity)
    try:
        await asyncio.get_event_loop().run_in_executor(None, repl.lobby_loop)
    finally:
        srv.close()
        await srv.wait_closed()
        Path(sock_path).unlink(missing_ok=True)


MID_COLUMN_WIDTH = 10  # fits "msg-XXXXXX"
MID_GUTTER = "  "       # two spaces


def _render_line(line: str, show_ids: bool) -> str:
    """Render an inbox/outbox line for output, with or without the MID column.

    The MID column width matches `msg-` (4 chars) + `secrets.token_hex(3)` (6 hex chars) = 10.
    If `broker_server._generate_id` ever produces longer IDs, the alignment degrades but
    output remains correct (Python's `:<10` left-pads but doesn't truncate).
    """
    from broker_format import split_mid_prefix
    mid, rest = split_mid_prefix(line)
    if not show_ids:
        return rest
    if mid is None:
        # Legacy line (pre-v1.5.0): no MID stored, render an em-dash placeholder.
        return f"{'—':<{MID_COLUMN_WIDTH}}{MID_GUTTER}{rest}"
    return f"{mid:<{MID_COLUMN_WIDTH}}{MID_GUTTER}{rest}"


async def run_oneshot(
    sock_path: str,
    identity: str,
    request_type: str,
    params: dict,
) -> dict:
    """Connect, send one request, return the response data, disconnect.

    Raises ConnectionError if the broker server is unreachable.
    Raises ValueError if the server returns an error response.
    """
    client = BrokerClient(identity=identity, sock_path=sock_path)
    try:
        await client.connect()
    except (ConnectionRefusedError, FileNotFoundError):
        raise ConnectionError(f"Cannot connect to broker at {sock_path}. Is the broker server running?")
    try:
        msg = {"type": request_type, **params}
        response = await client._request(msg)
        return response
    finally:
        await client.close()


def cmd_recv_inbox(
    identity: str,
    timeout: int,
    burst_window: int,
    show_ids: bool,
) -> int:
    """Receive the next batch of inbox messages.

    Behavior:
    - If the inbox already has unread backlog at startup, emit it and start the
      burst window immediately, ignoring `timeout`.
    - Otherwise wait up to `timeout` seconds for the first arrival. If
      `timeout=0`, wait indefinitely. Exit cleanly (code 0) with empty stdout
      if the timer expires with no traffic.
    - On first arrival, continue tailing for `burst_window` seconds. New lines
      arriving within the window are emitted. Exit when the window expires.
    - `burst_window=0` exits as soon as the first arrival has been delivered;
      a multi-line backlog at startup is emitted in one go (no waiting between
      lines) before exit.
    - Cursor advances per inbox-read batch (matches today's `broker follow`).
    """
    import time
    import threading
    from broker_storage import InboxLog, CursorStore

    sock_path = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
    root_dir = Path(os.environ.get(
        "MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker"),
    ))
    inbox = InboxLog(root_dir / "inbox")
    cursors = CursorStore(root_dir / "cursors")

    connected = threading.Event()
    socket_closed = threading.Event()
    connect_error: dict[str, str] = {}

    async def run_socket() -> None:
        client = BrokerClient(identity=identity, sock_path=sock_path, mode="follow")
        try:
            await client.connect()
        except (ConnectionRefusedError, FileNotFoundError):
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}. Is the broker server running?"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        except ValueError as exc:
            connect_error["msg"] = str(exc)
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        except Exception as exc:
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}: {exc}"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        connected.set()
        try:
            if client._listener_task is not None:
                await client._listener_task
        finally:
            socket_closed.set()
            try:
                await client.close()
            except Exception:
                pass

    def thread_target() -> None:
        asyncio.run(run_socket())

    socket_thread = threading.Thread(target=thread_target, daemon=True)
    socket_thread.start()

    if not connected.wait(timeout=5):
        print(
            f"Cannot connect to broker at {sock_path} (handshake timeout). Is the broker server running?",
            file=sys.stderr,
        )
        return 1
    if connect_error:
        print(connect_error["msg"], file=sys.stderr)
        return 1

    poll_interval = 0.2
    start = time.monotonic()
    first_arrival_at: float | None = None

    while True:
        if socket_closed.is_set():
            print("[broker] server disconnected", file=sys.stderr)
            return 1
        offset = cursors.get(identity)
        lines, new_offset = inbox.read_from(identity, offset)
        if lines:
            for line in lines:
                print(_render_line(line, show_ids), flush=True)
            cursors.set(identity, new_offset)
            if first_arrival_at is None:
                first_arrival_at = time.monotonic()
                if burst_window == 0:
                    return 0

        now = time.monotonic()
        if first_arrival_at is None:
            if timeout > 0 and now - start >= timeout:
                return 0
        else:
            if now - first_arrival_at >= burst_window:
                return 0

        time.sleep(poll_interval)


def cmd_follow_inbox(identity: str, idle_timeout: int, show_ids: bool) -> int:
    """Tail the per-identity DM inbox log and hold an open socket for presence.

    Delivery is file-based (the inbox log is the source of truth). The socket
    exists only as a presence beacon: server-side `who` reflects open follow
    connections. If the server stops or rejects the follow, this function exits
    non-zero.
    """
    import time
    import threading
    from broker_storage import InboxLog, CursorStore

    sock_path = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
    root_dir = Path(os.environ.get(
        "MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker"),
    ))
    inbox = InboxLog(root_dir / "inbox")
    cursors = CursorStore(root_dir / "cursors")

    connected = threading.Event()
    socket_closed = threading.Event()
    connect_error: dict[str, str] = {}

    async def run_socket() -> None:
        client = BrokerClient(identity=identity, sock_path=sock_path, mode="follow")
        try:
            await client.connect()
        except (ConnectionRefusedError, FileNotFoundError):
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}. Is the broker server running?"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()  # release main thread to read the error
            return
        except ValueError as exc:
            connect_error["msg"] = str(exc)
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        except Exception as exc:
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}: {exc}"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        connected.set()
        try:
            # Hold the socket open. _listen runs in the background; when it exits
            # (server EOF), set socket_closed so the file-tail loop can stop.
            if client._listener_task is not None:
                await client._listener_task
        finally:
            socket_closed.set()
            try:
                await client.close()
            except Exception:
                pass

    def thread_target() -> None:
        asyncio.run(run_socket())

    socket_thread = threading.Thread(target=thread_target, daemon=True)
    socket_thread.start()

    # Wait for the socket to either connect or fail.
    if not connected.wait(timeout=5):
        print(f"Cannot connect to broker at {sock_path} (handshake timeout). Is the broker server running?", file=sys.stderr)
        return 1
    if connect_error:
        print(connect_error["msg"], file=sys.stderr)
        return 1

    poll_interval = 0.2
    last_activity = time.monotonic()
    while True:
        if socket_closed.is_set():
            print("[broker] server disconnected", file=sys.stderr)
            return 1
        offset = cursors.get(identity)
        lines, new_offset = inbox.read_from(identity, offset)
        if lines:
            for line in lines:
                print(_render_line(line, show_ids), flush=True)
            cursors.set(identity, new_offset)
            last_activity = time.monotonic()
        if idle_timeout > 0 and time.monotonic() - last_activity >= idle_timeout:
            return 0
        time.sleep(poll_interval)


def _run_and_print(
    sock_path: str,
    identity: str,
    request_type: str,
    params: dict,
) -> None:
    """Run a one-shot request and print JSON result to stdout."""
    try:
        result = asyncio.run(run_oneshot(sock_path, identity, request_type, params))
        print(json.dumps(result, indent=2))
    except (ValueError, ConnectionError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


DEFAULT_SOCKET = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
DEFAULT_ROOT = Path(os.environ.get("MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker")))


class _VersionUnavailable(Exception):
    """Raised when plugin.json cannot be read, parsed, or validated."""


def _read_plugin_version(repo_root: Path) -> str:
    """Read the version field from <repo_root>/.claude-plugin/plugin.json.

    Raises _VersionUnavailable on any read, parse, or schema failure.
    """
    plugin_json = repo_root / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _VersionUnavailable() from exc
    if not isinstance(data, dict):
        raise _VersionUnavailable()
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise _VersionUnavailable()
    return version


def _resolve_repo_root() -> Path:
    """Walk from the resolved script path up one directory to the repo root."""
    return Path(__file__).resolve().parent.parent


class _VersionAction(argparse.Action):
    """Print `broker {version}` and exit. Reads plugin.json on demand."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = argparse.SUPPRESS,
        default: str = argparse.SUPPRESS,
        help: str = "Print broker version and exit",
    ) -> None:
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        try:
            version = _read_plugin_version(_resolve_repo_root())
        except _VersionUnavailable:
            print("broker: could not determine version", file=sys.stderr)
            sys.exit(1)
        print(f"broker {version}")
        sys.exit(0)


def _validate_identity_arg(value: str) -> str:
    """Argparse type validator for --identity.

    Rejects identity strings that look like a malformed orchestrator name —
    bare `@orchestrator` (no scope), or anything matching `@orchestrator/...`
    that doesn't fully validate as `@orchestrator/<scope>`. Other identities
    starting with `@orchestrator` (e.g. `@orchestrators/foo`, a peer identity
    that happens to share a prefix) pass through unchanged.

    Peer identity strings are unauthenticated, so we don't validate them here.
    """
    from broker_constants import ORCHESTRATOR_RE
    is_orchestrator_shaped = value == "@orchestrator" or value.startswith("@orchestrator/")
    if is_orchestrator_shaped and not ORCHESTRATOR_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            f"'--identity {value}' is reserved-prefix-shaped but not a valid orchestrator identity. "
            f"Use --identity @orchestrator/<scope> where <scope> matches [A-Za-z0-9._-]{{1,64}}."
        )
    return value


def _resolve_identity(explicit: str | None) -> str:
    """Resolve identity: --identity arg > BROKER_IDENTITY env > .broker/config.json > cwd derivation.

    Malformed orchestrator-shaped values from BROKER_IDENTITY are warned about
    and skipped, mirroring the .broker/config.json path. The explicit `--identity`
    flag is already validated by argparse so we trust it as-is.
    """
    if explicit is not None:
        return explicit
    env_identity = os.environ.get("BROKER_IDENTITY")
    if env_identity:
        from broker_constants import ORCHESTRATOR_RE
        if env_identity.startswith("@orchestrator") and not ORCHESTRATOR_RE.fullmatch(env_identity):
            print(
                f"broker: ignoring malformed BROKER_IDENTITY={env_identity!r} "
                f"(does not match @orchestrator/<scope> pattern); falling through to derivation.",
                file=sys.stderr,
            )
        else:
            return env_identity
    from broker_identity import derive_identity, IdentityDerivationError
    try:
        return derive_identity(Path.cwd())
    except IdentityDerivationError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Message broker for multi-agent DM communication")
    parser.add_argument("-V", "--version", action=_VersionAction)
    subparsers = parser.add_subparsers(dest="command")

    p_server = subparsers.add_parser("server", help="Start the broker server with an interactive REPL")
    p_server.add_argument("--identity", default="user", type=_validate_identity_arg,
                          help="Identity for this REPL session (default: user)")
    p_server.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_server.add_argument("--root-dir", type=Path, default=DEFAULT_ROOT,
                          help="Broker root directory (env: MCP_BROKER_ROOT)")

    p_send = subparsers.add_parser("send", help="Send a DM to one or more identities")
    p_send.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Sender identity (defaults to cwd-derived)")
    p_send.add_argument("--to", required=True, help="Comma-separated recipient identities")
    p_send.add_argument("content", help="Message content")
    p_send.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    p_bcast = subparsers.add_parser("broadcast", help="Broadcast to every registered identity")
    p_bcast.add_argument("--identity", required=False, type=_validate_identity_arg,
                         help="Sender identity (defaults to cwd-derived)")
    p_bcast.add_argument("content", help="Message content")
    p_bcast.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    p_ra = subparsers.add_parser("reply-all", help="Reply to all recipients of a prior DM (excluding self)")
    p_ra.add_argument("--identity", required=False, type=_validate_identity_arg,
                      help="Sender identity (defaults to cwd-derived)")
    p_ra.add_argument("--to-message", required=True, help="Message ID of the original DM")
    p_ra.add_argument("content", help="Message content")
    p_ra.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    p_read = subparsers.add_parser("read", help="Drain your DM inbox (advances the cursor)")
    p_read.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_read.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_read.add_argument("--show-ids", action="store_true",
                        help="Prefix each line with the message ID for use with reply-all.")

    p_follow = subparsers.add_parser(
        "follow",
        help="Tail your DM inbox log. Drains backlog, then waits for new messages until idle-timeout elapses.",
    )
    p_follow.add_argument("--identity", required=False, type=_validate_identity_arg,
                          help="Your identity (defaults to cwd-derived)")
    p_follow.add_argument("--idle-timeout", type=int, default=120,
                          help="Exit after N seconds of silence. 0 disables. Default: 120.")
    p_follow.add_argument("--show-ids", action="store_true",
                          help="Prefix each emitted line with the message ID.")

    p_recv = subparsers.add_parser(
        "recv",
        help="Receive the next batch of inbox messages. Blocks for the first arrival, then drains follow-ups for --burst-window seconds.",
    )
    p_recv.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_recv.add_argument("--timeout", type=int, default=0,
                        help="Max seconds to wait for the first message. 0 (default) waits indefinitely. Ignored if the inbox already has unread backlog at startup.")
    p_recv.add_argument("--burst-window", type=int, default=5,
                        help="Seconds to keep tailing for follow-ups after the first arrival. Default 5. 0 exits as soon as the first arrival has been delivered.")
    p_recv.add_argument("--show-ids", action="store_true",
                        help="Prefix each emitted line with the message ID.")

    p_hist = subparsers.add_parser("history", help="Read inbox (or outbox with --sent) without advancing cursor")
    p_hist.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_hist.add_argument("--from", dest="from_filter", help="Only lines from this sender")
    p_hist.add_argument("--since", help="Only lines with timestamp >= this ISO8601 string")
    p_hist.add_argument("--sent", action="store_true", help="Read the sender's outbox instead of inbox")
    p_hist.add_argument("--show-ids", action="store_true",
                        help="Prefix each line with the message ID.")
    p_hist.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    p_clients = subparsers.add_parser("clients", help="List identities currently connected to the broker")
    p_clients.add_argument("--identity", required=False, type=_validate_identity_arg,
                           help="Your identity (defaults to cwd-derived)")
    p_clients.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    subparsers.add_parser("whoami", help="Print the identity derived from cwd")

    p_init = subparsers.add_parser("init", help="Create .broker/config.json in the current directory")
    p_init.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Identity to pin (defaults to cwd-derived)")
    p_init.add_argument("--force", action="store_true",
                        help="Overwrite an existing .broker/config.json without confirmation")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)
    elif args.command == "server":
        asyncio.run(run_server_mode(args.identity, args.root_dir, args.socket))
    elif args.command == "send":
        identity = _resolve_identity(args.identity)
        recipients = [r.strip() for r in args.to.split(",") if r.strip()]
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "send_dm", {
                "to": recipients, "content": args.content,
            }))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(result["message_id"])
    elif args.command == "broadcast":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "send_broadcast",
                                             {"content": args.content}))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(result["message_id"])
    elif args.command == "reply-all":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "reply_all", {
                "to_message": args.to_message, "content": args.content,
            }))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(result["message_id"])
    elif args.command == "history":
        identity = _resolve_identity(args.identity)
        params: dict = {}
        if args.from_filter:
            params["from"] = args.from_filter
        if args.since:
            params["since"] = args.since
        if args.sent:
            params["sent"] = True
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "history_inbox", params))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        for line in result.get("lines", []):
            print(_render_line(line, args.show_ids))
    elif args.command == "read":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "read_inbox", {}))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        for line in result.get("lines", []):
            print(_render_line(line, args.show_ids))
    elif args.command == "follow":
        identity = _resolve_identity(args.identity)
        sys.exit(cmd_follow_inbox(identity, args.idle_timeout, args.show_ids))
    elif args.command == "recv":
        identity = _resolve_identity(args.identity)
        sys.exit(cmd_recv_inbox(identity, args.timeout, args.burst_window, args.show_ids))
    elif args.command == "clients":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "list_clients", {}))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        live = result.get("live", [])
        offline = result.get("offline", [])
        if not live and not offline:
            print("(no live followers, no registered identities)")
        for entry in live:
            print(f"{entry['identity']}       live, since {entry['since']}")
        for entry in offline:
            last_seen = entry.get("lastSeenAt", "—")
            print(f"{entry['identity']}       offline, last seen {last_seen}")
    elif args.command == "whoami":
        identity = _resolve_identity(None)
        print(f"{identity}  (from {Path.cwd()})")
    elif args.command == "init":
        cfg_path = Path.cwd() / ".broker" / "config.json"
        if args.identity is not None:
            identity = args.identity
        else:
            identity = _resolve_identity(None)
        # Idempotent / overwrite handling.
        if cfg_path.exists():
            try:
                existing = json.loads(cfg_path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = {}
            if existing.get("identity") == identity:
                print(f"no change: .broker/config.json already pins identity {identity!r}.")
                sys.exit(0)
            if not args.force:
                print(
                    f"error: .broker/config.json already pins identity "
                    f"{existing.get('identity')!r}. Re-run with --force to overwrite.",
                    file=sys.stderr,
                )
                sys.exit(1)
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({"identity": identity}, indent=2) + "\n")
        print(f"wrote {cfg_path} (identity: {identity})")


if __name__ == "__main__":
    main()
