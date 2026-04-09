#!/usr/bin/env python3
"""Interactive REPL CLI for the MCP message broker."""

import argparse
import asyncio
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
        print(f"Error: Cannot connect to broker at {sock_path}. Is the broker server running?", file=sys.stderr)
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


def main() -> None:
    """Parse CLI args and start the REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive REPL for the MCP message broker"
    )
    parser.add_argument(
        "--identity", default="user",
        help="Identity for this session (default: user)",
    )
    parser.add_argument(
        "--server", action="store_true",
        help="Run as the broker server (starts socket + REPL)",
    )
    parser.add_argument(
        "--storage-dir", type=Path,
        default=Path.home() / ".mcp-broker" / "conversations",
        help="Directory for conversation files (default: ~/.mcp-broker/conversations)",
    )
    parser.add_argument(
        "--socket", type=str,
        default=str(Path.home() / ".mcp-broker" / "broker.sock"),
        help="Path to broker socket (default: ~/.mcp-broker/broker.sock)",
    )
    args = parser.parse_args()

    if args.server:
        asyncio.run(run_server_mode(args.identity, args.storage_dir, args.socket))
    else:
        asyncio.run(run_client_mode(args.identity, args.socket))


if __name__ == "__main__":
    main()
