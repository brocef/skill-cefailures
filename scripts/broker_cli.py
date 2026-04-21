#!/usr/bin/env python3
"""CLI for the multi-agent message broker."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


def format_conversation_line(conv: dict) -> str:
    """Format a conversation dict for display in the lobby list.

    Args:
        conv: A conversation summary dict with keys: id, topic, status,
              message_count, unread_count.

    Returns:
        A formatted string like: [id] "topic" (status, N msgs, M unread)
    """
    return (
        f'  [{conv["id"]}] "{conv["topic"]}" '
        f'({conv["status"]}, {conv["message_count"]} msgs, {conv["unread_count"]} unread)'
    )


def format_message(msg: dict) -> str:
    """Format a message dict for display.

    Args:
        msg: A message dict with keys: sender, content.

    Returns:
        A formatted string like: [sender] content
    """
    return f'  [{msg["sender"]}] {msg["content"]}'


def format_message_compact(msg: dict) -> str:
    """Format a message dict as a single compact line for agent consumption.

    Both user and system messages from history render identically via the
    sender/content fields: [sender] content. This is the agent-facing format;
    it has no leading indent and no timestamp (the server persists timestamps
    on disk for audit).

    Args:
        msg: A persisted message dict with keys: sender, content.
             Timestamps and ids are ignored here.

    Returns:
        A string like: "[server] Okay, on it"
    """
    return f"[{msg['sender']}] {msg['content']}"


LOBBY_HELP = """\
Commands:
  list             List all conversations
  create <topic>   Create a new conversation
  join <id>        Enter a conversation
  help             Show this help
  exit             Quit"""

CONVERSATION_HELP = """\
Commands:
  read     Show new messages
  members  Show who's in this conversation
  leave    Leave the conversation and return to lobby
  close    Close the conversation (read-only for everyone)
  back     Return to lobby (stay in conversation)
  help     Show this help
  <text>   Send a message"""


class ServerREPL:
    """REPL that runs inside the server process, using BrokerServer directly."""

    def __init__(self, server: BrokerServer, identity: str) -> None:
        self.server = server
        self.identity = identity
        self._req_counter = 0
        # Register as a client so we receive pushes
        self.server.connect(identity, self._on_push)
        self._current_conversation: str | None = None

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
        """Handle pushed messages — print if in the right conversation."""
        cid = msg.get("conversation_id")
        if cid == self._current_conversation:
            if msg["type"] == "message":
                print(f"\n{format_message(msg['message'])}")
            elif msg["type"] == "system":
                print(f"\n  * {msg['identity']} {msg['event']}ed" if msg['event'] == 'join' else f"\n  * {msg['identity']} left")

    def lobby_loop(self) -> None:
        """Run the lobby REPL loop."""
        while True:
            try:
                line = input("broker> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            parts = line.split(None, 1)
            command = parts[0].lower()
            try:
                if command == "exit":
                    return
                elif command == "list":
                    result = self._request({"type": "list_conversations"})
                    convs = result["conversations"]
                    if not convs:
                        print("  No conversations.")
                    else:
                        for conv in convs:
                            print(format_conversation_line(conv))
                elif command == "create":
                    if len(parts) < 2:
                        print("Usage: create <topic>", file=sys.stderr)
                        continue
                    try:
                        seed = input("  Seed message (Enter to skip): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        continue
                    msg = {"type": "create_conversation", "topic": parts[1]}
                    if seed:
                        msg["content"] = seed
                    result = self._request(msg)
                    print(f"  Created {result['conversation_id']}")
                elif command == "join":
                    if len(parts) < 2:
                        print("Usage: join <id>", file=sys.stderr)
                        continue
                    cid = parts[1].strip()
                    self._request({"type": "join_conversation", "conversation_id": cid})
                    self._current_conversation = cid
                    # Show history on join
                    result = self._request({"type": "history", "conversation_id": cid})
                    for msg in result["messages"]:
                        print(format_message(msg))
                    self._conversation_loop(cid)
                    self._current_conversation = None
                elif command == "help":
                    print(LOBBY_HELP)
                else:
                    print(f"Unknown command: {command}. Type 'help' for options.", file=sys.stderr)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)

    def _conversation_loop(self, conversation_id: str) -> None:
        """Run the conversation REPL loop."""
        while True:
            try:
                line = input(f"{conversation_id}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            command = line.lower()
            try:
                if command == "back":
                    return
                elif command == "leave":
                    self._request({"type": "leave_conversation", "conversation_id": conversation_id})
                    print(f"  Left {conversation_id}")
                    return
                elif command == "read":
                    result = self._request({"type": "history", "conversation_id": conversation_id})
                    for msg in result["messages"]:
                        print(format_message(msg))
                elif command == "members":
                    result = self._request({"type": "list_members", "conversation_id": conversation_id})
                    for member in result["members"]:
                        print(f"  {member}")
                elif command == "close":
                    self._request({"type": "close_conversation", "conversation_id": conversation_id})
                    print(f"  Closed {conversation_id}")
                    return
                elif command == "help":
                    print(CONVERSATION_HELP)
                else:
                    result = self._request({
                        "type": "send_message", "conversation_id": conversation_id, "content": line,
                    })
                    print(f"  Sent {result['message_id']}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)


class ClientREPL:
    """REPL that connects to a running broker server via socket."""

    def __init__(self, client: BrokerClient, loop: asyncio.AbstractEventLoop) -> None:
        self.client = client
        self.loop = loop
        self._current_conversation: str | None = None
        self._push_task: asyncio.Task | None = None

    def _request(self, coro) -> dict:  # type: ignore[type-arg]
        """Call an async coroutine from the sync REPL thread."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=5.0)

    def _start_push_printer(self) -> None:
        """Start a background task on the event loop that prints push messages."""
        self.client.on_push = asyncio.Queue()

        async def _printer() -> None:
            try:
                while True:
                    msg = await self.client.on_push.get()
                    cid = msg.get("conversation_id")
                    if cid == self._current_conversation:
                        if msg["type"] == "message":
                            print(f"\n{format_message(msg['message'])}")
                        elif msg["type"] == "system":
                            if msg["event"] == "join":
                                print(f"\n  * {msg['identity']} joined")
                            else:
                                print(f"\n  * {msg['identity']} left")
            except asyncio.CancelledError:
                pass

        self._push_task = asyncio.run_coroutine_threadsafe(
            _printer(), self.loop
        )

    def _stop_push_printer(self) -> None:
        """Cancel the push printer background task."""
        if self._push_task and not self._push_task.done():
            self._push_task.cancel()
        self.client.on_push = None

    def lobby_loop(self) -> None:
        """Run the lobby REPL loop."""
        self._start_push_printer()
        try:
            self._lobby_loop_inner()
        finally:
            self._stop_push_printer()

    def _lobby_loop_inner(self) -> None:
        """Inner lobby loop logic."""
        while True:
            try:
                line = input("broker> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            parts = line.split(None, 1)
            command = parts[0].lower()
            try:
                if command == "exit":
                    return
                elif command == "list":
                    result = self._request(self.client.list_conversations())
                    convs = result["conversations"]
                    if not convs:
                        print("  No conversations.")
                    else:
                        for conv in convs:
                            print(format_conversation_line(conv))
                elif command == "create":
                    if len(parts) < 2:
                        print("Usage: create <topic>", file=sys.stderr)
                        continue
                    try:
                        seed = input("  Seed message (Enter to skip): ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        continue
                    content = seed if seed else None
                    result = self._request(
                        self.client.create_conversation(parts[1], content=content)
                    )
                    print(f"  Created {result['conversation_id']}")
                elif command == "join":
                    if len(parts) < 2:
                        print("Usage: join <id>", file=sys.stderr)
                        continue
                    cid = parts[1].strip()
                    self._request(self.client.join_conversation(cid))
                    self._current_conversation = cid
                    # Show history on join
                    result = self._request(self.client.history(cid))
                    for msg in result["messages"]:
                        print(format_message(msg))
                    self._conversation_loop(cid)
                    self._current_conversation = None
                elif command == "help":
                    print(LOBBY_HELP)
                else:
                    print(f"Unknown command: {command}. Type 'help' for options.", file=sys.stderr)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)

    def _conversation_loop(self, conversation_id: str) -> None:
        """Run the conversation REPL loop."""
        while True:
            try:
                line = input(f"{conversation_id}> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not line:
                continue
            command = line.lower()
            try:
                if command == "back":
                    return
                elif command == "leave":
                    self._request(self.client.leave_conversation(conversation_id))
                    print(f"  Left {conversation_id}")
                    return
                elif command == "read":
                    result = self._request(self.client.history(conversation_id))
                    for msg in result["messages"]:
                        print(format_message(msg))
                elif command == "members":
                    result = self._request(self.client.list_members(conversation_id))
                    for member in result["members"]:
                        print(f"  {member}")
                elif command == "close":
                    self._request(self.client.close_conversation(conversation_id))
                    print(f"  Closed {conversation_id}")
                    return
                elif command == "help":
                    print(CONVERSATION_HELP)
                else:
                    result = self._request(
                        self.client.send_message(conversation_id, line)
                    )
                    print(f"  Sent {result['message_id']}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)


async def run_client_mode(identity: str, sock_path: str) -> None:
    """Connect to an existing broker server and run the REPL."""
    client = BrokerClient(identity=identity, sock_path=sock_path)
    try:
        await client.connect()
    except (ConnectionRefusedError, FileNotFoundError):
        print(json.dumps({"error": f"Cannot connect to broker at {sock_path}. Is the broker server running?"}), file=sys.stderr)
        sys.exit(1)

    print(f"Connected to broker at {sock_path}")
    loop = asyncio.get_event_loop()
    repl = ClientREPL(client, loop)
    try:
        await loop.run_in_executor(None, repl.lobby_loop)
    finally:
        await client.close()


async def run_server_mode(identity: str, storage_dir: Path, sock_path: str) -> None:
    """Start the socket server and run the REPL."""
    server = BrokerServer(storage_dir=storage_dir)
    srv = await start_server(server, sock_path)
    print(f"Broker server listening on {sock_path}")

    repl = ServerREPL(server, identity)
    try:
        # Run REPL in a thread so it doesn't block the event loop
        await asyncio.get_event_loop().run_in_executor(None, repl.lobby_loop)
    finally:
        srv.close()
        await srv.wait_closed()
        Path(sock_path).unlink(missing_ok=True)


async def run_oneshot(sock_path: str, identity: str, request_type: str, params: dict) -> dict:
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


async def cmd_follow(args: argparse.Namespace) -> int:
    client = BrokerClient(args.identity, args.socket)
    client.on_push = asyncio.Queue()

    try:
        await client.connect()
    except (FileNotFoundError, ConnectionRefusedError):
        print(json.dumps({
            "error": f"Cannot connect to broker at {args.socket}. Is the broker server running?",
        }), file=sys.stderr)
        return 1

    seen_ids: set[str] = set()
    try:
        history = await client.history(args.conversation_id)
        for msg in history["messages"]:
            seen_ids.add(msg["id"])
            _emit(msg, args)

        deadline = _compute_deadline(args.timeout)
        count = 0
        while True:
            timeout = _next_timeout(deadline, args.idle_timeout)
            get_task = asyncio.create_task(client.on_push.get())
            listener_task = client._listener_task  # type: ignore[attr-defined]

            waiters = {get_task}
            if listener_task is not None and not listener_task.done():
                waiters.add(listener_task)

            done, pending = await asyncio.wait(
                waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED,
            )

            if not done:
                # Timeout (idle or hard cap) elapsed — clean exit.
                get_task.cancel()
                break

            if listener_task is not None and listener_task in done:
                # Server-side socket closed. Abort with a clear error.
                get_task.cancel()
                print(json.dumps({
                    "error": "Broker socket closed unexpectedly. Is the broker server still running?",
                }), file=sys.stderr)
                return 1

            push = get_task.result()

            if push.get("conversation_id") != args.conversation_id:
                continue
            if push["type"] == "conversation_closed":
                break
            if push["type"] in ("message", "system"):
                msg = push["message"]
                if msg["id"] in seen_ids:
                    continue
                seen_ids.add(msg["id"])
                if _emit(msg, args):
                    count += 1
                    if args.count > 0 and count >= args.count:
                        break
    finally:
        await client.close()

    return 0


def _compute_deadline(hard_cap_seconds: int) -> float | None:
    """Absolute monotonic deadline, or None if disabled (hard_cap == 0)."""
    import time
    if hard_cap_seconds <= 0:
        return None
    return time.monotonic() + hard_cap_seconds


def _next_timeout(deadline: float | None, idle_seconds: int) -> float | None:
    """Compute the next asyncio.wait_for timeout: min(remaining deadline, idle).

    Returns None to wait forever (both disabled).
    """
    import time
    candidates = []
    if deadline is not None:
        candidates.append(max(0.0, deadline - time.monotonic()))
    if idle_seconds > 0:
        candidates.append(float(idle_seconds))
    if not candidates:
        return None
    return min(candidates)


def _emit(msg: dict, args: argparse.Namespace) -> bool:
    """Print a message per the requested format and system-filter.

    Returns True if the message was emitted, False if filtered out.
    """
    if msg["sender"] == "system" and not args.include_system:
        return False
    if args.format == "json":
        print(json.dumps({
            "id": msg["id"], "sender": msg["sender"],
            "content": msg["content"], "timestamp": msg["timestamp"],
        }), flush=True)
    else:
        print(format_message_compact(msg), flush=True)
    return True


def _run_and_print(sock_path: str, identity: str, request_type: str, params: dict) -> None:
    """Run a one-shot request and print JSON result to stdout."""
    try:
        result = asyncio.run(run_oneshot(sock_path, identity, request_type, params))
        print(json.dumps(result, indent=2))
    except (ValueError, ConnectionError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


DEFAULT_SOCKET = str(Path.home() / ".mcp-broker" / "broker.sock")
DEFAULT_STORAGE = Path.home() / ".mcp-broker" / "conversations"


def main() -> None:
    """Parse CLI args and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Message broker for multi-agent conversations"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- server ---
    p_server = subparsers.add_parser("server", help="Start the broker server and human REPL")
    p_server.add_argument("--identity", default="user", help="Identity for this session (default: user)")
    p_server.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_server.add_argument("--storage-dir", type=Path, default=DEFAULT_STORAGE, help="Conversation storage directory")

    # --- repl ---
    p_repl = subparsers.add_parser("repl", help="Connect to a running broker as a client REPL")
    p_repl.add_argument("--identity", default="user", help="Identity for this session (default: user)")
    p_repl.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- create ---
    p_create = subparsers.add_parser("create", help="Create a conversation")
    p_create.add_argument("--identity", required=True, help="Your identity")
    p_create.add_argument("topic", help="Conversation topic")
    p_create.add_argument("--content", help="Optional seed message")
    p_create.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- send ---
    p_send = subparsers.add_parser("send", help="Send a message")
    p_send.add_argument("--identity", required=True, help="Your identity")
    p_send.add_argument("conversation_id", help="Conversation ID")
    p_send.add_argument("content", help="Message content")
    p_send.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- read ---
    p_read = subparsers.add_parser("read", help="Read new messages")
    p_read.add_argument("--identity", required=True, help="Your identity")
    p_read.add_argument("conversation_id", help="Conversation ID")
    p_read.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_read.add_argument("--format", choices=["json", "compact"], default="json",
                        help="Output format. 'compact' emits [sender] content lines (agent-facing). Default: json.")

    # --- follow ---
    p_follow = subparsers.add_parser(
        "follow",
        help="Stream new messages from a conversation. Drains backlog, then "
             "consumes pushes until idle-timeout, total timeout, count, or "
             "conversation_closed. Use foreground to block until a reply arrives.",
    )
    p_follow.add_argument("--identity", required=True, help="Your identity")
    p_follow.add_argument("conversation_id", help="Conversation ID")
    p_follow.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")
    p_follow.add_argument("--idle-timeout", type=int, default=120,
                          help="Exit after N seconds of silence. 0 disables. Default: 120.")
    p_follow.add_argument("--timeout", type=int, default=600,
                          help="Hard cap in seconds. 0 disables. Default: 600.")
    p_follow.add_argument("--count", type=int, default=0,
                          help="Exit after N messages received. 0 disables. Default: 0.")
    p_follow.add_argument("--include-system", action="store_true",
                          help="Include system join/leave events in the stream. "
                               "Default: suppressed.")
    p_follow.add_argument("--format", choices=["compact", "json"], default="compact",
                          help="Output format. Default: compact.")

    # --- list ---
    p_list = subparsers.add_parser("list", help="List conversations")
    p_list.add_argument("--identity", required=True, help="Your identity")
    p_list.add_argument("--status", choices=["open", "closed"], help="Filter by status")
    p_list.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- members ---
    p_members = subparsers.add_parser("members", help="List conversation members")
    p_members.add_argument("--identity", required=True, help="Your identity")
    p_members.add_argument("conversation_id", help="Conversation ID")
    p_members.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- join ---
    p_join = subparsers.add_parser("join", help="Join a conversation")
    p_join.add_argument("--identity", required=True, help="Your identity")
    p_join.add_argument("conversation_id", help="Conversation ID")
    p_join.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- leave ---
    p_leave = subparsers.add_parser("leave", help="Leave a conversation")
    p_leave.add_argument("--identity", required=True, help="Your identity")
    p_leave.add_argument("conversation_id", help="Conversation ID")
    p_leave.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    # --- close ---
    p_close = subparsers.add_parser("close", help="Close a conversation")
    p_close.add_argument("--identity", required=True, help="Your identity")
    p_close.add_argument("conversation_id", help="Conversation ID")
    p_close.add_argument("--socket", default=DEFAULT_SOCKET, help="Socket path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)
    elif args.command == "server":
        asyncio.run(run_server_mode(args.identity, args.storage_dir, args.socket))
    elif args.command == "repl":
        asyncio.run(run_client_mode(args.identity, args.socket))
    elif args.command == "create":
        params = {"topic": args.topic}
        if args.content:
            params["content"] = args.content
        _run_and_print(args.socket, args.identity, "create_conversation", params)
    elif args.command == "send":
        _run_and_print(args.socket, args.identity, "send_message", {
            "conversation_id": args.conversation_id, "content": args.content,
        })
    elif args.command == "read":
        if args.format == "compact":
            try:
                result = asyncio.run(run_oneshot(args.socket, args.identity, "history", {
                    "conversation_id": args.conversation_id,
                }))
            except (ValueError, ConnectionError) as e:
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                sys.exit(1)
            for msg in result.get("messages", []):
                print(format_message_compact(msg), flush=True)
        else:
            _run_and_print(args.socket, args.identity, "history", {
                "conversation_id": args.conversation_id,
            })
    elif args.command == "follow":
        sys.exit(asyncio.run(cmd_follow(args)))
    elif args.command == "list":
        params = {}
        if args.status:
            params["status"] = args.status
        _run_and_print(args.socket, args.identity, "list_conversations", params)
    elif args.command == "members":
        _run_and_print(args.socket, args.identity, "list_members", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "join":
        _run_and_print(args.socket, args.identity, "join_conversation", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "leave":
        _run_and_print(args.socket, args.identity, "leave_conversation", {
            "conversation_id": args.conversation_id,
        })
    elif args.command == "close":
        _run_and_print(args.socket, args.identity, "close_conversation", {
            "conversation_id": args.conversation_id,
        })


if __name__ == "__main__":
    main()
