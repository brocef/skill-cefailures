#!/usr/bin/env python3
"""Wire the MCP broker into a project's .claude/settings.json."""

import argparse
import json
import sys
from pathlib import Path

BROKER_SCRIPT = Path(__file__).resolve().parent / "mcp_broker.py"


def install_broker(
    identity: str,
    project_dir: Path,
    storage_dir: Path | None = None,
) -> None:
    """Add the broker MCP server entry to the project's settings.json."""
    claude_dir = project_dir / ".claude"
    if not claude_dir.is_dir():
        print(f"Error: {claude_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    settings_path = claude_dir / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    else:
        settings = {}

    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    broker_args = [str(BROKER_SCRIPT), "--identity", identity]
    if storage_dir:
        broker_args.extend(["--storage-dir", str(storage_dir)])

    settings["mcpServers"]["broker"] = {
        "command": sys.executable,
        "args": broker_args,
        "type": "stdio",
    }

    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Installed broker (identity={identity}) in {settings_path}")


def remove_broker(project_dir: Path) -> None:
    """Remove the broker entry from the project's settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    if not settings_path.exists():
        print("Warning: settings.json not found", file=sys.stderr)
        return

    settings = json.loads(settings_path.read_text())
    mcp_servers = settings.get("mcpServers", {})

    if "broker" not in mcp_servers:
        print("Warning: broker is not configured in settings.json", file=sys.stderr)
        return

    del mcp_servers["broker"]
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"Removed broker from {settings_path}")


def main() -> None:
    """Parse CLI args and install or remove the broker."""
    parser = argparse.ArgumentParser(
        description="Install or remove the MCP broker in a project's .claude/settings.json."
    )
    parser.add_argument("--identity", help="Identity for this connection (e.g. 'agent_a')")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )
    parser.add_argument("--storage-dir", type=Path, help="Custom storage directory for conversations")
    parser.add_argument("--remove", action="store_true", help="Remove the broker entry")

    args = parser.parse_args()

    if args.remove:
        remove_broker(project_dir=args.project_dir)
    else:
        if not args.identity:
            print("Error: --identity is required for installation", file=sys.stderr)
            sys.exit(1)
        install_broker(
            identity=args.identity,
            project_dir=args.project_dir,
            storage_dir=args.storage_dir,
        )


if __name__ == "__main__":
    main()
