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
    (tmp_path / "package.json").write_text(json.dumps({"name": "proposit-server"}))
    assert derive_identity(tmp_path) == "proposit-server"


def test_package_json_missing_name_falls_through_to_git(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"version": "1.0.0"}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "git@github.com:Proposit-App/proposit-mobile.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Proposit-App/proposit-mobile"


def test_git_remote_https_url(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/Proposit-App/proposit-core.git"], cwd=tmp_path, check=True)
    assert derive_identity(tmp_path) == "Proposit-App/proposit-core"


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
