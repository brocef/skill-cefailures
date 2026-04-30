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


def _find_nearest_broker_config(start: Path, ceiling: Path | None = None) -> Path | None:
    """Walk up from `start` looking for `.broker/config.json`.

    Stops at the first match, at the directory immediately below `ceiling` (so
    we don't escape into the user's parent directories), or at the filesystem
    root, whichever comes first. `ceiling` defaults to `Path.home()` so a stray
    config in `/` doesn't get applied to every workspace.
    """
    if ceiling is None:
        ceiling = Path.home()
    ceiling = ceiling.resolve()
    current = start.resolve()
    while True:
        candidate = current / ".broker" / "config.json"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        if current == ceiling:
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
      1. `.broker/config.json` walking up from cwd, if present and well-formed.
         The file's `identity` field is validated: malformed identities log a
         stderr warning and fall through.
      2. Nearest `package.json` going up; if its `name` field is a non-empty string, use it.
      3. Otherwise, parse `git remote get-url origin` into `<org>/<repo>`.
      4. Otherwise, raise `IdentityDerivationError`.
    """
    import sys as _sys
    from broker_constants import ORCHESTRATOR_RE

    cfg_path = _find_nearest_broker_config(cwd)
    if cfg_path is not None:
        identity = _read_identity_from_config(cfg_path)
        if identity is not None:
            # Validate orchestrator-prefix-shaped identities the same way the
            # CLI validator does — don't connect under a malformed name.
            if identity.startswith("@orchestrator") and not ORCHESTRATOR_RE.fullmatch(identity):
                print(
                    f"broker: ignoring malformed identity {identity!r} in {cfg_path} "
                    f"(does not match @orchestrator/<scope> pattern)",
                    file=_sys.stderr,
                )
            else:
                return identity

    pkg = _find_nearest_package_json(cwd)
    if pkg is not None:
        name = _identity_from_package_json(pkg)
        if name is not None:
            return name
    remote = _identity_from_git_remote(cwd)
    if remote is not None:
        return remote
    raise IdentityDerivationError(
        f"Cannot derive identity from {cwd}: no .broker/config.json, no package.json with name, no git remote origin."
    )


def _read_identity_from_config(path: Path) -> str | None:
    """Read the `identity` field from `.broker/config.json`, or None on any error.

    Malformed JSON or missing field is non-fatal: log a stderr warning and return None.
    """
    import sys as _sys
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        print(f"broker: ignoring malformed .broker/config.json at {path}", file=_sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"broker: ignoring .broker/config.json at {path} (not an object)", file=_sys.stderr)
        return None
    identity = data.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        return None
    return identity.strip()
