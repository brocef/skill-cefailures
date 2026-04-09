#!/usr/bin/env python3
"""Wire the MCP broker into a project's .mcp.json."""

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
    """Add the broker MCP server entry to the project's .mcp.json."""
    if not project_dir.is_dir():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    mcp_path = project_dir / ".mcp.json"
    if mcp_path.exists():
        config = json.loads(mcp_path.read_text())
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    broker_args = [str(BROKER_SCRIPT), "--identity", identity]
    if storage_dir:
        broker_args.extend(["--storage-dir", str(storage_dir)])

    config["mcpServers"]["broker"] = {
        "command": sys.executable,
        "args": broker_args,
        "type": "stdio",
    }

    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Installed broker (identity={identity}) in {mcp_path}")


def remove_broker(project_dir: Path) -> None:
    """Remove the broker entry from the project's .mcp.json."""
    mcp_path = project_dir / ".mcp.json"
    if not mcp_path.exists():
        print("Warning: .mcp.json not found", file=sys.stderr)
        return

    config = json.loads(mcp_path.read_text())
    mcp_servers = config.get("mcpServers", {})

    if "broker" not in mcp_servers:
        print("Warning: broker is not configured in .mcp.json", file=sys.stderr)
        return

    del mcp_servers["broker"]
    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"Removed broker from {mcp_path}")


def main() -> None:
    """Parse CLI args and install or remove the broker."""
    parser = argparse.ArgumentParser(
        description="Install or remove the MCP broker in a project's .mcp.json."
    )
    parser.add_argument("path", type=Path, help="Path to the project repo")
    parser.add_argument("--identity", help="Identity for this connection (e.g. 'agent_a')")
    parser.add_argument("--storage-dir", type=Path, help="Custom storage directory for conversations")
    parser.add_argument("--remove", action="store_true", help="Remove the broker entry")

    args = parser.parse_args()

    if args.remove:
        remove_broker(project_dir=args.path)
    else:
        if not args.identity:
            print("Error: --identity is required for installation", file=sys.stderr)
            sys.exit(1)
        install_broker(
            identity=args.identity,
            project_dir=args.path,
            storage_dir=args.storage_dir,
        )


if __name__ == "__main__":
    main()
