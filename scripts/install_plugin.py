#!/usr/bin/env python3
"""Symlink hook plugins into ~/.claude/hooks/ and register them in settings.json."""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"
HOOKS_DIR = Path.home() / ".claude" / "hooks"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"


def get_available_plugins() -> list[str]:
    """Return names of all valid plugins (directories containing a .sh file)."""
    if not PLUGINS_DIR.exists():
        return []
    return sorted(
        d.name for d in PLUGINS_DIR.iterdir()
        if d.is_dir() and list(d.glob("*.sh"))
    )


def get_plugin_scripts(name: str) -> list[Path]:
    """Return all .sh files in a plugin directory."""
    return sorted((PLUGINS_DIR / name).glob("*.sh"))


def load_plugin_config(name: str) -> dict:
    """Load plugin.json metadata for a plugin."""
    config_path = PLUGINS_DIR / name / "plugin.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid plugin.json in plugins/{name}/: {e}", file=sys.stderr)
        sys.exit(1)


def load_settings() -> dict:
    """Load ~/.claude/settings.json, returning empty dict if missing."""
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    """Write settings back to ~/.claude/settings.json."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def register_hooks(name: str) -> None:
    """Add hook entries from plugin.json into settings.json."""
    config = load_plugin_config(name)
    hook_defs = config.get("hooks", {})
    if not hook_defs:
        return

    settings = load_settings()
    hooks = settings.setdefault("hooks", {})
    scripts = get_plugin_scripts(name)

    for event, opts in hook_defs.items():
        matcher = opts.get("matcher", ".*")
        event_hooks = hooks.setdefault(event, [])

        for script in scripts:
            command = f"bash ~/.claude/hooks/{script.name}"

            # Check if this exact hook is already registered
            already_registered = False
            for entry in event_hooks:
                for h in entry.get("hooks", []):
                    if h.get("command") == command:
                        already_registered = True
                        break
                if already_registered:
                    break

            if already_registered:
                print(f"Hook already registered: {event} -> {command}")
                continue

            entry = {
                "matcher": matcher,
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                    }
                ],
            }
            event_hooks.append(entry)
            print(f"Registered hook: {event} ({matcher}) -> {command}")

    save_settings(settings)


def unregister_hooks(name: str) -> None:
    """Remove hook entries for this plugin from settings.json."""
    config = load_plugin_config(name)
    hook_defs = config.get("hooks", {})
    if not hook_defs:
        return

    settings = load_settings()
    hooks = settings.get("hooks", {})
    scripts = get_plugin_scripts(name)
    commands = {f"bash ~/.claude/hooks/{s.name}" for s in scripts}

    for event in hook_defs:
        event_hooks = hooks.get(event, [])
        filtered = []
        for entry in event_hooks:
            entry_hooks = [
                h for h in entry.get("hooks", [])
                if h.get("command") not in commands
            ]
            if entry_hooks:
                entry["hooks"] = entry_hooks
                filtered.append(entry)
        if filtered:
            hooks[event] = filtered
        elif event in hooks:
            del hooks[event]

    if not hooks:
        settings.pop("hooks", None)
    else:
        settings["hooks"] = hooks

    save_settings(settings)
    print(f"Unregistered hooks for {name}")


def install_plugin(name: str, force: bool = False) -> None:
    """Create symlinks and register hooks for a single plugin."""
    source_dir = PLUGINS_DIR / name
    scripts = get_plugin_scripts(name)
    if not scripts:
        print(f"Error: No .sh files found in plugins/{name}/", file=sys.stderr)
        sys.exit(1)

    HOOKS_DIR.mkdir(parents=True, exist_ok=True)

    for script in scripts:
        target = HOOKS_DIR / script.name

        if target.exists() or target.is_symlink():
            if not force:
                print(f"Warning: {target} already exists. Use --force to overwrite.", file=sys.stderr)
                continue
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                print(f"Error: {target} is a directory, not a file. Remove it manually.", file=sys.stderr)
                sys.exit(1)

        target.symlink_to(script)
        print(f"Installed: {target} -> {script}")

    register_hooks(name)


def remove_plugin(name: str) -> None:
    """Remove symlinks and unregister hooks for a single plugin."""
    scripts = get_plugin_scripts(name)
    if not scripts:
        print(f"Warning: No .sh files found in plugins/{name}/", file=sys.stderr)
        return

    for script in scripts:
        target = HOOKS_DIR / script.name
        if not target.is_symlink():
            print(f"Warning: {target} is not a symlink or doesn't exist.", file=sys.stderr)
            continue
        target.unlink()
        print(f"Removed: {target}")

    unregister_hooks(name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install or remove hook plugins for Claude Code."
    )
    parser.add_argument("name", nargs="?", help="Plugin name to install")
    parser.add_argument("--all", action="store_true", help="Install all available plugins")
    parser.add_argument("--remove", action="store_true", help="Remove (uninstall) the plugin")
    parser.add_argument("--force", action="store_true", help="Overwrite existing symlinks")
    parser.add_argument("--list", action="store_true", help="List available plugins")

    args = parser.parse_args()

    if args.list:
        plugins = get_available_plugins()
        if plugins:
            print("Available plugins:")
            for p in plugins:
                scripts = get_plugin_scripts(p)
                installed = all((HOOKS_DIR / s.name).is_symlink() for s in scripts)
                mark = "✓" if installed else " "
                print(f"  [{mark}] {p}")
        else:
            print("No plugins found in plugins/ directory.")
        return

    if args.all:
        plugins = get_available_plugins()
        if not plugins:
            print("No plugins found in plugins/ directory.")
            return
        for p in plugins:
            if args.remove:
                remove_plugin(p)
            else:
                install_plugin(p, force=args.force)
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    if args.remove:
        remove_plugin(args.name)
    else:
        install_plugin(args.name, force=args.force)


if __name__ == "__main__":
    main()
