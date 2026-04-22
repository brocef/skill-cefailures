#!/usr/bin/env python3
"""Derive a stable identity string from a working directory."""

import json
import re
import subprocess
from pathlib import Path


class IdentityDerivationError(ValueError):
    """Raised when no identity can be derived from the cwd."""


def _find_nearest_package_json(start: Path) -> Path | None:
    """Walk up from `start` to find the nearest package.json. Returns None if none found."""
    current = start.resolve()
    while True:
        candidate = current / "package.json"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _identity_from_package_json(pkg_path: Path) -> str | None:
    """Return the package name, or None if missing/empty."""
    try:
        data = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        return name
    return None


def _identity_from_git_remote(cwd: Path) -> str | None:
    """Parse `git remote get-url origin` into `<org>/<repo>`, or None."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    url = result.stdout.strip()
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def derive_identity(cwd: Path) -> str:
    """Compute the canonical identity for an agent running at `cwd`.

    Rules (in order):
      1. Nearest `package.json` going up; if its `name` field is a non-empty string, use it verbatim.
      2. Otherwise, parse `git remote get-url origin` into `<org>/<repo>`.
      3. Otherwise, raise `IdentityDerivationError`.
    """
    pkg = _find_nearest_package_json(cwd)
    if pkg is not None:
        name = _identity_from_package_json(pkg)
        if name is not None:
            return name
    remote = _identity_from_git_remote(cwd)
    if remote is not None:
        return remote
    raise IdentityDerivationError(
        f"Cannot derive identity from {cwd}: no package.json with name, no git remote origin."
    )
