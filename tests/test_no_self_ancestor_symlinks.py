"""Guard against tracked symlinks that resolve to their own ancestor.

A symlink whose target contains the symlink itself makes the tree infinitely
deep (``plugins/x -> ..`` gives ``plugins/x/plugins/x/...``). Any component
scan that follows symlinks recurses forever — including the server-side one
claude.ai runs when syncing a marketplace, which cannot be configured around.

This asserts the class, not one path: pinning a known-bad path by name would
only stop that exact path from coming back.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYMLINK_MODE = "120000"


def tracked_symlinks() -> list[Path]:
    """Return repo-relative paths of every symlink tracked by git."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    paths = []
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        if meta.split()[0] == SYMLINK_MODE:
            paths.append(Path(path))
    return paths


def resolves_to_own_ancestor(link: Path) -> bool:
    """True if ``link``'s target is the link itself or a directory containing it."""
    target = Path((REPO_ROOT / link).readlink())
    resolved = target if target.is_absolute() else (link.parent / target)
    # Normalize ".." lexically; the path need not exist, so avoid resolve().
    parts: list[str] = []
    for part in resolved.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    normalized = Path(*parts) if parts else Path(".")
    return normalized == Path(".") or normalized == link or normalized in link.parents


def test_no_tracked_symlink_resolves_to_its_own_ancestor() -> None:
    offenders = [str(p) for p in tracked_symlinks() if resolves_to_own_ancestor(p)]
    assert not offenders, (
        "these tracked symlinks contain themselves, making the tree infinitely "
        f"deep for any scanner that follows symlinks: {offenders}"
    )


if __name__ == "__main__":
    test_no_tracked_symlink_resolves_to_its_own_ancestor()
    print("ok")
