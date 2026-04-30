#!/usr/bin/env python3
"""Merge recommended permission rules into ~/.claude/settings.json."""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "recommended-permissions.json"
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"


def load_recommended(path: Path) -> dict:
    """Load the recommended permissions data file."""
    with open(path) as f:
        return json.load(f)


def flatten_categories(categorized: dict) -> list[str]:
    """Flatten a categorized permission dict into a flat list."""
    result: list[str] = []
    for rules in categorized.values():
        result.extend(rules)
    return result


def load_settings(path: Path) -> dict:
    """Load existing settings, or return empty dict if file doesn't exist or is empty."""
    if not path.exists():
        return {}
    content = path.read_text().strip()
    if not content:
        return {}
    return json.loads(content)


def save_settings(path: Path, settings: dict) -> None:
    """Write settings back to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def list_categories(data: dict) -> None:
    """Print available categories and their rule counts."""
    for section in ("allow", "deny"):
        categories = data["permissions"].get(section, {})
        if not categories:
            continue
        print(f"\n{section.upper()}:")
        for cat, rules in categories.items():
            print(f"  {cat}: {len(rules)} rule(s)")
            for rule in rules:
                print(f"    - {rule}")


def merge_permissions(
    settings: dict,
    data: dict,
    include: list[str] | None,
    exclude: list[str] | None,
) -> tuple[int, int]:
    """Merge recommended permissions into settings. Returns (added_allow, added_deny)."""
    allow_cats = data["permissions"].get("allow", {})
    deny_cats = data["permissions"].get("deny", {})

    if include:
        allow_cats = {k: v for k, v in allow_cats.items() if k in include}
        deny_cats = {k: v for k, v in deny_cats.items() if k in include}
    if exclude:
        allow_cats = {k: v for k, v in allow_cats.items() if k not in exclude}
        deny_cats = {k: v for k, v in deny_cats.items() if k not in exclude}

    new_allow = flatten_categories(allow_cats)
    new_deny = flatten_categories(deny_cats)

    if "permissions" not in settings:
        settings["permissions"] = {}
    existing_allow = set(settings["permissions"].get("allow", []))
    existing_deny = set(settings["permissions"].get("deny", []))

    added_allow = [r for r in new_allow if r not in existing_allow]
    added_deny = [r for r in new_deny if r not in existing_deny]

    settings["permissions"]["allow"] = sorted(
        existing_allow | set(new_allow)
    )
    settings["permissions"]["deny"] = sorted(
        existing_deny | set(new_deny)
    )

    return len(added_allow), len(added_deny)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply recommended permission rules to ~/.claude/settings.json."
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available categories and exit",
    )
    parser.add_argument(
        "--include", nargs="+", metavar="CAT",
        help="Only apply these categories (e.g., --include git file_operations)",
    )
    parser.add_argument(
        "--exclude", nargs="+", metavar="CAT",
        help="Skip these categories (e.g., --exclude mcp_broker pnpm)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be added without writing",
    )
    parser.add_argument(
        "--data-file", type=Path, default=DATA_FILE,
        help=f"Path to permissions data file (default: {DATA_FILE})",
    )
    parser.add_argument(
        "--settings-file", type=Path, default=SETTINGS_FILE,
        help=f"Path to settings.json (default: {SETTINGS_FILE})",
    )

    args = parser.parse_args()

    if not args.data_file.exists():
        print(f"Error: Data file not found: {args.data_file}", file=sys.stderr)
        sys.exit(1)

    data = load_recommended(args.data_file)

    if args.list:
        list_categories(data)
        return

    if args.include and args.exclude:
        print("Error: Cannot use both --include and --exclude.", file=sys.stderr)
        sys.exit(1)

    settings = load_settings(args.settings_file)
    added_allow, added_deny = merge_permissions(
        settings, data, args.include, args.exclude,
    )

    if added_allow == 0 and added_deny == 0:
        print("No new rules to add — settings already up to date.")
        return

    if args.dry_run:
        print(f"Would add {added_allow} allow rule(s) and {added_deny} deny rule(s).")
        print("\nResulting permissions:")
        print(json.dumps(settings["permissions"], indent=2))
        return

    save_settings(args.settings_file, settings)
    print(f"Added {added_allow} allow rule(s) and {added_deny} deny rule(s) to {args.settings_file}")


if __name__ == "__main__":
    main()
