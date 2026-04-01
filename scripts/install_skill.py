#!/usr/bin/env python3
"""Symlink library skills into ~/.claude/skills/ for Claude Code discovery."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TARGET_DIR = Path.home() / ".claude" / "skills"


def get_available_skills() -> list[str]:
    """Return names of all valid skills (directories containing SKILL.md)."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def install_skill(name: str, force: bool = False) -> None:
    """Create symlink for a single skill."""
    source = SKILLS_DIR / name
    if not (source / "SKILL.md").exists():
        print(f"Error: No SKILL.md found in skills/{name}/", file=sys.stderr)
        sys.exit(1)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    target = TARGET_DIR / name

    if target.exists() or target.is_symlink():
        if not force:
            print(f"Warning: {target} already exists. Use --force to overwrite.", file=sys.stderr)
            return
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            print(f"Error: {target} is a real directory, not a symlink. Remove it manually.", file=sys.stderr)
            sys.exit(1)

    target.symlink_to(source)
    print(f"Installed: {target} -> {source}")


def remove_skill(name: str) -> None:
    """Remove symlink for a single skill."""
    target = TARGET_DIR / name
    if not target.is_symlink():
        print(f"Warning: {target} is not a symlink or doesn't exist.", file=sys.stderr)
        return
    target.unlink()
    print(f"Removed: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="Install or remove library skills for Claude Code."
    )
    parser.add_argument("name", nargs="?", help="Skill name to install")
    parser.add_argument("--all", action="store_true", help="Install all available skills")
    parser.add_argument("--remove", action="store_true", help="Remove (uninstall) the skill")
    parser.add_argument("--remove-all", action="store_true", help="Remove all installed skills")
    parser.add_argument("--force", action="store_true", help="Overwrite existing symlinks")
    parser.add_argument("--list", action="store_true", help="List available skills")

    args = parser.parse_args()

    if args.list:
        skills = get_available_skills()
        if skills:
            print("Available skills:")
            for s in skills:
                installed = "✓" if (TARGET_DIR / s).is_symlink() else " "
                print(f"  [{installed}] {s}")
        else:
            print("No skills found in skills/ directory.")
        return

    if args.remove_all:
        args.all = True
        args.remove = True

    if args.all:
        skills = get_available_skills()
        if not skills:
            print("No skills found in skills/ directory.")
            return
        for s in skills:
            if args.remove:
                remove_skill(s)
            else:
                install_skill(s, force=args.force)
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    if args.remove:
        remove_skill(args.name)
    else:
        install_skill(args.name, force=args.force)


if __name__ == "__main__":
    main()
