# tests/test_broker_identity.py
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_identity import derive_identity, IdentityDerivationError


def test_package_json_name_wins(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "@scope/pkg"}))
    assert derive_identity(tmp_path) == "@scope/pkg"


def test_package_json_unscoped(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "acme-api"}))
    assert derive_identity(tmp_path) == "acme-api"


def test_package_json_missing_name_falls_through_to_git(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"version": "1.0.0"}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:Example-Org/example-mobile.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Example-Org/example-mobile"


def test_git_remote_https_url(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/Example-Org/example-core.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Example-Org/example-core"


def test_no_package_no_git_raises(tmp_path: Path) -> None:
    with pytest.raises(IdentityDerivationError):
        derive_identity(tmp_path)


def test_nearest_package_json_from_subdir(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "outer"}))
    inner = tmp_path / "pkg"
    inner.mkdir()
    (inner / "package.json").write_text(json.dumps({"name": "inner"}))
    assert derive_identity(inner) == "inner"


def test_walks_up_to_find_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "root"}))
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert derive_identity(deep) == "root"


# --- Task 12: _find_nearest_broker_config walk-up helper ---

def test_find_nearest_broker_config_returns_none_when_absent(tmp_path: Path) -> None:
    from broker_identity import _find_nearest_broker_config
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert _find_nearest_broker_config(sub, ceiling=tmp_path) is None


def test_find_nearest_broker_config_finds_in_cwd(tmp_path: Path) -> None:
    from broker_identity import _find_nearest_broker_config
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@myorg/projectA"}')
    found = _find_nearest_broker_config(tmp_path, ceiling=tmp_path.parent)
    # The result should be the cfg path (after Path.resolve()).
    assert found == cfg.resolve()


def test_find_nearest_broker_config_walks_up(tmp_path: Path) -> None:
    from broker_identity import _find_nearest_broker_config
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@myorg/projectA"}')
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    found = _find_nearest_broker_config(deep, ceiling=tmp_path.parent)
    assert found == cfg.resolve()


def test_find_nearest_broker_config_stops_at_ceiling(tmp_path: Path) -> None:
    """Config above the ceiling is invisible (don't escape the user's home dir)."""
    from broker_identity import _find_nearest_broker_config
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@myorg/projectA"}')
    sub = tmp_path / "a"
    sub.mkdir()
    # Ceiling = sub means we won't see tmp_path's config.
    assert _find_nearest_broker_config(sub, ceiling=sub) is None


# --- Task 13: derive_identity reads .broker/config.json + BROKER_IDENTITY env ---

def test_derive_identity_prefers_broker_config(tmp_path: Path, monkeypatch) -> None:
    """If .broker/config.json exists with a valid identity, it overrides cwd-derivation."""
    from broker_identity import derive_identity
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@myorg/pinned"}')
    # Even with a package.json present, the config file wins.
    (tmp_path / "package.json").write_text('{"name": "different-name"}')
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert derive_identity(tmp_path) == "@myorg/pinned"


def test_derive_identity_ignores_malformed_broker_config(tmp_path: Path, monkeypatch, capsys) -> None:
    """Malformed JSON in .broker/config.json: warn on stderr, fall through to derivation."""
    from broker_identity import derive_identity
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text("not json at all{")
    (tmp_path / "package.json").write_text('{"name": "fallback-name"}')
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert derive_identity(tmp_path) == "fallback-name"
    err = capsys.readouterr().err
    assert "malformed" in err.lower()
    assert "config.json" in err


def test_derive_identity_ignores_missing_identity_field(tmp_path: Path, monkeypatch, capsys) -> None:
    from broker_identity import derive_identity
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"unrelated": "field"}')
    (tmp_path / "package.json").write_text('{"name": "fallback"}')
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert derive_identity(tmp_path) == "fallback"


def test_derive_identity_rejects_invalid_orchestrator_in_config(tmp_path: Path, monkeypatch, capsys) -> None:
    """A config-file identity that fails the orchestrator charset check is rejected with a warning."""
    from broker_identity import derive_identity
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@orchestrator/foo bar"}')
    (tmp_path / "package.json").write_text('{"name": "fallback"}')
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert derive_identity(tmp_path) == "fallback"
    err = capsys.readouterr().err
    assert "@orchestrator/foo bar" in err


def test_resolve_identity_honors_BROKER_IDENTITY_env(tmp_path: Path, monkeypatch) -> None:
    """The CLI helper _resolve_identity must prefer BROKER_IDENTITY env over derivation."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from broker_cli import _resolve_identity
    monkeypatch.setenv("BROKER_IDENTITY", "@myorg/from-env")
    monkeypatch.chdir(tmp_path)
    assert _resolve_identity(None) == "@myorg/from-env"


def test_resolve_identity_explicit_arg_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from broker_cli import _resolve_identity
    monkeypatch.setenv("BROKER_IDENTITY", "@myorg/from-env")
    monkeypatch.chdir(tmp_path)
    assert _resolve_identity("alice") == "alice"


def test_resolve_identity_warns_on_malformed_BROKER_IDENTITY(tmp_path: Path, monkeypatch, capsys) -> None:
    """Malformed orchestrator-shaped BROKER_IDENTITY warns and falls through to derivation."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from broker_cli import _resolve_identity
    monkeypatch.setenv("BROKER_IDENTITY", "@orchestrator/foo bar")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text('{"name": "fallback"}')
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert _resolve_identity(None) == "fallback"
    err = capsys.readouterr().err
    assert "@orchestrator/foo bar" in err
    assert "BROKER_IDENTITY" in err


# --- Closest-source precedence: a package.json closer to cwd than a parent's
# .broker/config.json must win. Models the org/projectA monorepo layout where
# /org/.broker/config.json pins @org and /org/projectA/package.json names @org/projectA.

def test_cwd_package_json_beats_parent_broker_config(tmp_path: Path, monkeypatch) -> None:
    """A package.json in cwd should win over a .broker/config.json one level up."""
    org = tmp_path / "org"
    project = org / "projectA"
    project.mkdir(parents=True)
    cfg = org / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@org"}')
    (project / "package.json").write_text(json.dumps({"name": "@org/projectA"}))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert derive_identity(project) == "@org/projectA"


def test_orchestrator_root_still_resolves_to_config(tmp_path: Path, monkeypatch) -> None:
    """At the orchestrator root, .broker/config.json still wins (no package.json there)."""
    org = tmp_path / "org"
    org.mkdir()
    cfg = org / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@org"}')
    (org / "projectA").mkdir()
    (org / "projectA" / "package.json").write_text(json.dumps({"name": "@org/projectA"}))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert derive_identity(org) == "@org"


def test_subdir_finds_project_package_json_before_parent_config(tmp_path: Path, monkeypatch) -> None:
    """Deep inside a project, the nearest package.json beats a parent's config."""
    org = tmp_path / "org"
    project = org / "projectA"
    deep = project / "src" / "utils"
    deep.mkdir(parents=True)
    cfg = org / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@org"}')
    (project / "package.json").write_text(json.dumps({"name": "@org/projectA"}))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert derive_identity(deep) == "@org/projectA"


def test_same_dir_broker_config_still_beats_package_json(tmp_path: Path, monkeypatch) -> None:
    """When config and package.json sit in the same dir, config still wins (explicit pin)."""
    cfg = tmp_path / ".broker" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text('{"identity": "@myorg/pinned"}')
    (tmp_path / "package.json").write_text(json.dumps({"name": "@myorg/derived"}))
    monkeypatch.setenv("HOME", str(tmp_path.parent))
    assert derive_identity(tmp_path) == "@myorg/pinned"


def test_nested_broker_config_beats_outer_broker_config(tmp_path: Path, monkeypatch) -> None:
    """An inner .broker/config.json beats an outer one (closest wins)."""
    outer = tmp_path / "org"
    inner = outer / "projectA"
    inner.mkdir(parents=True)
    outer_cfg = outer / ".broker" / "config.json"
    outer_cfg.parent.mkdir()
    outer_cfg.write_text('{"identity": "@org"}')
    inner_cfg = inner / ".broker" / "config.json"
    inner_cfg.parent.mkdir()
    inner_cfg.write_text('{"identity": "@org/projectA-pinned"}')
    monkeypatch.setenv("HOME", str(tmp_path))
    assert derive_identity(inner) == "@org/projectA-pinned"
