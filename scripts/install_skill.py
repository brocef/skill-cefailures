#!/usr/bin/env python3
"""Symlink library skills into agent-specific skill directories."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CLAUDE_TARGET_DIR = Path.home() / ".claude" / "skills"
CODEX_TARGET_DIR = Path.home() / ".codex" / "skills"
TARGET_DIR = CLAUDE_TARGET_DIR
AGENT_TARGETS = {
    "claude": CLAUDE_TARGET_DIR,
    "codex": CODEX_TARGET_DIR,
}


def get_available_skills() -> list[str]:
    """Return names of all valid skills (directories containing SKILL.md)."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def install_skill(name: str, force: bool = False, target_dir: Path | None = None) -> None:
    """Create symlink for a single skill."""
    source = SKILLS_DIR / name
    if not (source / "SKILL.md").exists():
        print(f"Error: No SKILL.md found in skills/{name}/", file=sys.stderr)
        sys.exit(1)

    target_root = target_dir or TARGET_DIR
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / name

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


def remove_skill(name: str, target_dir: Path | None = None) -> None:
    """Remove symlink for a single skill."""
    target = (target_dir or TARGET_DIR) / name
    if not target.is_symlink():
        print(f"Warning: {target} is not a symlink or doesn't exist.", file=sys.stderr)
        return
    target.unlink()
    print(f"Removed: {target}")


def main():
    parser = argparse.ArgumentParser(
        description="Install or remove library skills for Claude Code or Codex."
    )
    parser.add_argument("name", nargs="?", help="Skill name to install")
    parser.add_argument(
        "--agent",
        choices=["claude", "codex", "all"],
        default="claude",
        help="Agent skill directory to target (default: claude)",
    )
    parser.add_argument("--all", action="store_true", help="Install all available skills")
    parser.add_argument("--remove", action="store_true", help="Remove (uninstall) the skill")
    parser.add_argument("--remove-all", action="store_true", help="Remove all installed skills")
    parser.add_argument("--force", action="store_true", help="Overwrite existing symlinks")
    parser.add_argument("--list", action="store_true", help="List available skills")

    args = parser.parse_args()
    target_dirs = (
        list(AGENT_TARGETS.values())
        if args.agent == "all"
        else [AGENT_TARGETS[args.agent]]
    )

    if args.list:
        skills = get_available_skills()
        if skills:
            print("Available skills:")
            for s in skills:
                installed_count = sum(1 for target_dir in target_dirs if (target_dir / s).is_symlink())
                if len(target_dirs) == 1:
                    installed = "✓" if installed_count else " "
                else:
                    installed = str(installed_count)
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
            for target_dir in target_dirs:
                if args.remove:
                    remove_skill(s, target_dir=target_dir)
                else:
                    install_skill(s, force=args.force, target_dir=target_dir)
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    if args.remove:
        for target_dir in target_dirs:
            remove_skill(args.name, target_dir=target_dir)
    else:
        for target_dir in target_dirs:
            install_skill(args.name, force=args.force, target_dir=target_dir)


if __name__ == "__main__":
    main()
