import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "install_plugin.py")

import install_plugin


@pytest.fixture
def plugin_dirs(tmp_path, monkeypatch):
    """Set up isolated plugins, hooks, and settings paths."""
    plugins_dir = tmp_path / "plugins"
    hooks_dir = tmp_path / "hooks"
    settings_path = tmp_path / "settings.json"
    plugins_dir.mkdir()
    hooks_dir.mkdir()
    monkeypatch.setattr(install_plugin, "PLUGINS_DIR", plugins_dir)
    monkeypatch.setattr(install_plugin, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(install_plugin, "SETTINGS_PATH", settings_path)
    return plugins_dir, hooks_dir, settings_path


def _create_plugin(plugins_dir: Path, name: str, hooks: dict | None = None) -> Path:
    """Create a minimal plugin directory with a .sh script and optional plugin.json."""
    plugin_dir = plugins_dir / name
    plugin_dir.mkdir()
    script = plugin_dir / f"{name}.sh"
    script.write_text("#!/bin/bash\necho ok")
    if hooks is not None:
        config = {"description": f"Test plugin {name}", "hooks": hooks}
        (plugin_dir / "plugin.json").write_text(json.dumps(config))
    return plugin_dir


def test_install_plugin_help():
    """Verify the script runs and shows help."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "install" in result.stdout.lower()


def test_load_plugin_config_invalid_json(plugin_dirs):
    """Verify load_plugin_config exits on malformed plugin.json."""
    plugins_dir, _, _ = plugin_dirs
    plugin_dir = plugins_dir / "bad-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text("not json{{{")

    with pytest.raises(SystemExit):
        install_plugin.load_plugin_config("bad-plugin")
