#!/usr/bin/env python3
"""Interactive REPL CLI for the MCP message broker."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_broker import ConversationStore


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
  read    Show new messages
  close   Close the conversation and return to lobby
  back    Return to lobby
  help    Show this help
  <text>  Send a message"""


def lobby_loop(store: ConversationStore) -> None:
    """Run the lobby REPL loop.

    Args:
        store: The ConversationStore instance to use for all operations.
    """
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

        if command == "exit":
            return
        elif command == "list":
            _handle_list(store)
        elif command == "create":
            if len(parts) < 2:
                print("Usage: create <topic>", file=sys.stderr)
                continue
            _handle_create(store, parts[1])
        elif command == "join":
            if len(parts) < 2:
                print("Usage: join <id>", file=sys.stderr)
                continue
            _handle_join(store, parts[1].strip())
        elif command == "help":
            print(LOBBY_HELP)
        else:
            print(f"Unknown command: {command}. Type 'help' for options.", file=sys.stderr)


def _handle_list(store: ConversationStore) -> None:
    """List all conversations."""
    try:
        result = store.list_conversations()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return
    convs = result["conversations"]
    if not convs:
        print("  No conversations.")
        return
    for conv in convs:
        print(format_conversation_line(conv))


def _handle_create(store: ConversationStore, topic: str) -> None:
    """Create a conversation with an optional seed message."""
    try:
        seed = input("  Seed message (Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    try:
        if seed:
            result = store.create_conversation(topic, content=seed)
        else:
            result = store.create_conversation(topic)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    cid = result["conversation_id"]
    print(f"  Created {cid}")

    if seed:
        # The seed message was already sent via create_conversation.
        # Find its ID from the file to display it.
        try:
            conv_data = store._load(cid)
            if conv_data["messages"]:
                msg_id = conv_data["messages"][-1]["id"]
                print(f"  Sent {msg_id}")
        except Exception:
            pass


def _handle_join(store: ConversationStore, conversation_id: str) -> None:
    """Enter a conversation and run the conversation loop."""
    # Verify the conversation exists
    try:
        store._load(conversation_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    # Show unread messages on join
    _show_new_messages(store, conversation_id)

    # Enter conversation loop
    conversation_loop(store, conversation_id)


def _show_new_messages(store: ConversationStore, conversation_id: str) -> None:
    """Read and display new messages for a conversation."""
    try:
        result = store.read_new_messages(conversation_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return
    for msg in result["messages"]:
        print(format_message(msg))


def conversation_loop(store: ConversationStore, conversation_id: str) -> None:
    """Run the conversation REPL loop.

    Args:
        store: The ConversationStore instance.
        conversation_id: The ID of the conversation to interact with.
    """
    while True:
        try:
            line = input(f"{conversation_id}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue

        command = line.lower()

        if command == "read":
            _show_new_messages(store, conversation_id)
        elif command == "close":
            try:
                store.close_conversation(conversation_id)
                print(f"  Closed {conversation_id}")
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
            return
        elif command == "back":
            return
        elif command == "help":
            print(CONVERSATION_HELP)
        else:
            # Anything else is sent as a message
            try:
                result = store.send_message(conversation_id, line)
                print(f"  Sent {result['message_id']}")
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


def main() -> None:
    """Parse CLI args and start the REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive REPL for the MCP message broker"
    )
    parser.add_argument(
        "--identity",
        default="user",
        help="Identity for this session (default: user)",
    )
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=Path.home() / ".mcp-broker" / "conversations",
        help="Directory for conversation files (default: ~/.mcp-broker/conversations)",
    )
    args = parser.parse_args()

    store = ConversationStore(identity=args.identity, storage_dir=args.storage_dir)
    lobby_loop(store)


if __name__ == "__main__":
    main()
