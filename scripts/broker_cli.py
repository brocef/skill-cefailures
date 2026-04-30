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

    def __init__(self, server: BrokerServer, identity: str, token: str | None = None) -> None:
        self.server = server
        self.identity = identity
        self._req_counter = 0
        self.server.connect(identity, self._on_push, token=token)
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
            clients = data["clients"]
            if not clients:
                print("  (no clients connected)")
            else:
                for name in clients:
                    marker = " (you)" if name == self.identity else ""
                    print(f"  {name}{marker}")
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
    identity: str, root_dir: Path, sock_path: str, token: str | None = None,
) -> None:
    """Start the socket server and run the REPL."""
    server = BrokerServer(root_dir=root_dir)
    srv = await start_server(server, sock_path)
    print(f"Broker server listening on {sock_path}")

    repl = ServerREPL(server, identity, token=token)
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
    token: str | None = None,
) -> dict:
    """Connect, send one request, return the response data, disconnect.

    Raises ConnectionError if the broker server is unreachable.
    Raises ValueError if the server returns an error response.
    """
    client = BrokerClient(identity=identity, sock_path=sock_path, token=token)
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


def cmd_follow_inbox(identity: str, idle_timeout: int, show_ids: bool) -> int:
    """Tail the per-identity DM inbox log, starting from cursor, exiting on idle."""
    import time
    from broker_storage import InboxLog, CursorStore

    root_dir = Path(os.environ.get(
        "MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker"),
    ))
    inbox = InboxLog(root_dir / "inbox")
    cursors = CursorStore(root_dir / "cursors")

    poll_interval = 0.2
    last_activity = time.monotonic()

    while True:
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
    token: str | None = None,
) -> None:
    """Run a one-shot request and print JSON result to stdout."""
    try:
        result = asyncio.run(run_oneshot(sock_path, identity, request_type, params, token=token))
        print(json.dumps(result, indent=2))
    except (ValueError, ConnectionError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


DEFAULT_SOCKET = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
DEFAULT_ROOT = Path(os.environ.get("MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker")))
DEFAULT_TOKEN = os.environ.get("BROKER_TOKEN")


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


def _add_token_arg(p: argparse.ArgumentParser) -> None:
    """Add --token to a subparser, defaulting to BROKER_TOKEN env var if set."""
    p.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help="Token for reserved identities (env: BROKER_TOKEN). Required only for orchestrator/human.",
    )


def _resolve_identity(explicit: str | None) -> str:
    """Resolve identity: --identity arg > BROKER_IDENTITY env > .broker/config.json > cwd derivation."""
    if explicit is not None:
        return explicit
    env_identity = os.environ.get("BROKER_IDENTITY")
    if env_identity:
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
    _add_token_arg(p_server)

    p_send = subparsers.add_parser("send", help="Send a DM to one or more identities")
    p_send.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Sender identity (defaults to cwd-derived)")
    p_send.add_argument("--to", required=True, help="Comma-separated recipient identities")
    p_send.add_argument("content", help="Message content")
    p_send.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    _add_token_arg(p_send)

    p_bcast = subparsers.add_parser("broadcast", help="Broadcast to every registered identity")
    p_bcast.add_argument("--identity", required=False, type=_validate_identity_arg,
                         help="Sender identity (defaults to cwd-derived)")
    p_bcast.add_argument("content", help="Message content")
    p_bcast.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    _add_token_arg(p_bcast)

    p_ra = subparsers.add_parser("reply-all", help="Reply to all recipients of a prior DM (excluding self)")
    p_ra.add_argument("--identity", required=False, type=_validate_identity_arg,
                      help="Sender identity (defaults to cwd-derived)")
    p_ra.add_argument("--to-message", required=True, help="Message ID of the original DM")
    p_ra.add_argument("content", help="Message content")
    p_ra.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    _add_token_arg(p_ra)

    p_read = subparsers.add_parser("read", help="Drain your DM inbox (advances the cursor)")
    p_read.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_read.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_read.add_argument("--show-ids", action="store_true",
                        help="Prefix each line with the message ID for use with reply-all.")
    _add_token_arg(p_read)

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

    p_hist = subparsers.add_parser("history", help="Read inbox (or outbox with --sent) without advancing cursor")
    p_hist.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_hist.add_argument("--from", dest="from_filter", help="Only lines from this sender")
    p_hist.add_argument("--since", help="Only lines with timestamp >= this ISO8601 string")
    p_hist.add_argument("--sent", action="store_true", help="Read the sender's outbox instead of inbox")
    p_hist.add_argument("--show-ids", action="store_true",
                        help="Prefix each line with the message ID.")
    p_hist.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    _add_token_arg(p_hist)

    p_clients = subparsers.add_parser("clients", help="List identities currently connected to the broker")
    p_clients.add_argument("--identity", required=False, type=_validate_identity_arg,
                           help="Your identity (defaults to cwd-derived)")
    p_clients.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    _add_token_arg(p_clients)

    subparsers.add_parser("whoami", help="Print the identity derived from cwd")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)
    elif args.command == "server":
        asyncio.run(run_server_mode(args.identity, args.root_dir, args.socket, token=args.token))
    elif args.command == "send":
        identity = _resolve_identity(args.identity)
        recipients = [r.strip() for r in args.to.split(",") if r.strip()]
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "send_dm", {
                "to": recipients, "content": args.content,
            }, token=args.token))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(result["message_id"])
    elif args.command == "broadcast":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "send_broadcast",
                                             {"content": args.content}, token=args.token))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        print(result["message_id"])
    elif args.command == "reply-all":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "reply_all", {
                "to_message": args.to_message, "content": args.content,
            }, token=args.token))
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
            result = asyncio.run(run_oneshot(args.socket, identity, "history_inbox", params, token=args.token))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        for line in result.get("lines", []):
            print(_render_line(line, args.show_ids))
    elif args.command == "read":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "read_inbox", {}, token=args.token))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        for line in result.get("lines", []):
            print(_render_line(line, args.show_ids))
    elif args.command == "follow":
        identity = _resolve_identity(args.identity)
        sys.exit(cmd_follow_inbox(identity, args.idle_timeout, args.show_ids))
    elif args.command == "clients":
        identity = _resolve_identity(args.identity)
        try:
            result = asyncio.run(run_oneshot(args.socket, identity, "list_clients", {}, token=args.token))
        except (ValueError, ConnectionError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        for name in result.get("clients", []):
            print(name)
    elif args.command == "whoami":
        from broker_identity import derive_identity, IdentityDerivationError
        try:
            identity = derive_identity(Path.cwd())
        except IdentityDerivationError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"{identity}  (from {Path.cwd()})")


if __name__ == "__main__":
    main()
