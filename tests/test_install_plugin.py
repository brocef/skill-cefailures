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


def test_get_available_plugins(plugin_dirs):
    """Verify get_available_plugins filters directories without .sh files."""
    plugins_dir, _, _ = plugin_dirs
    _create_plugin(plugins_dir, "valid-plugin")
    # Directory without .sh files should be excluded
    (plugins_dir / "no-scripts").mkdir()
    (plugins_dir / "no-scripts" / "readme.txt").write_text("not a script")

    result = install_plugin.get_available_plugins()
    assert result == ["valid-plugin"]


def test_load_plugin_config(plugin_dirs):
    """Verify load_plugin_config returns config dict or empty dict."""
    plugins_dir, _, _ = plugin_dirs
    _create_plugin(plugins_dir, "with-config", hooks={"PermissionRequest": {"matcher": ".*"}})

    config = install_plugin.load_plugin_config("with-config")
    assert config["hooks"]["PermissionRequest"]["matcher"] == ".*"

    # Plugin without config returns empty dict
    _create_plugin(plugins_dir, "no-config")
    assert install_plugin.load_plugin_config("no-config") == {}


def test_install_plugin_creates_symlinks(plugin_dirs):
    """Verify install_plugin symlinks .sh files into hooks directory."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    install_plugin.install_plugin("my-plugin")

    target = hooks_dir / "my-plugin.sh"
    assert target.is_symlink()
    assert target.resolve() == (plugins_dir / "my-plugin" / "my-plugin.sh").resolve()


def test_install_plugin_force_overwrites(plugin_dirs):
    """Verify --force replaces existing symlink."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    # Create existing symlink pointing elsewhere
    target = hooks_dir / "my-plugin.sh"
    target.symlink_to("/tmp")

    install_plugin.install_plugin("my-plugin", force=True)

    assert target.is_symlink()
    assert target.resolve() == (plugins_dir / "my-plugin" / "my-plugin.sh").resolve()


def test_install_plugin_conflict_without_force(plugin_dirs, capsys):
    """Verify warning when target exists without --force."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={})

    # Create an existing symlink
    target = hooks_dir / "my-plugin.sh"
    target.symlink_to("/tmp")

    install_plugin.install_plugin("my-plugin", force=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_install_plugin_no_scripts(plugin_dirs):
    """Verify sys.exit when plugin has no .sh files."""
    plugins_dir, _, _ = plugin_dirs
    (plugins_dir / "empty-plugin").mkdir()

    with pytest.raises(SystemExit):
        install_plugin.install_plugin("empty-plugin")


def test_remove_plugin(plugin_dirs):
    """Verify remove_plugin removes symlinks and unregisters hooks."""
    plugins_dir, hooks_dir, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.install_plugin("my-plugin")
    assert (hooks_dir / "my-plugin.sh").is_symlink()

    install_plugin.remove_plugin("my-plugin")
    assert not (hooks_dir / "my-plugin.sh").exists()


def test_register_hooks(plugin_dirs):
    """Verify register_hooks writes hook entries to settings.json."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    event_hooks = settings["hooks"]["PermissionRequest"]
    assert len(event_hooks) == 1
    assert event_hooks[0]["matcher"] == ".*"
    assert event_hooks[0]["hooks"][0]["command"] == "bash ~/.claude/hooks/my-plugin.sh"


def test_register_hooks_dedup(plugin_dirs):
    """Verify already-registered hooks are not duplicated."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.register_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    event_hooks = settings["hooks"]["PermissionRequest"]
    assert len(event_hooks) == 1


def test_unregister_hooks(plugin_dirs):
    """Verify unregister_hooks removes hook entries from settings.json."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.unregister_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    assert "PermissionRequest" not in settings.get("hooks", {})


def test_unregister_hooks_cleans_empty(plugin_dirs):
    """Verify empty hooks dict is removed from settings entirely."""
    plugins_dir, _, settings_path = plugin_dirs
    _create_plugin(plugins_dir, "my-plugin", hooks={"PermissionRequest": {"matcher": ".*"}})

    install_plugin.register_hooks("my-plugin")
    install_plugin.unregister_hooks("my-plugin")

    settings = json.loads(settings_path.read_text())
    assert "hooks" not in settings


def test_install_all_plugins(plugin_dirs):
    """Verify installing all available plugins."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "plugin-a", hooks={})
    _create_plugin(plugins_dir, "plugin-b", hooks={})

    for p in install_plugin.get_available_plugins():
        install_plugin.install_plugin(p)

    assert (hooks_dir / "plugin-a.sh").is_symlink()
    assert (hooks_dir / "plugin-b.sh").is_symlink()


def test_remove_all_plugins(plugin_dirs):
    """Verify removing all installed plugins."""
    plugins_dir, hooks_dir, _ = plugin_dirs
    _create_plugin(plugins_dir, "plugin-a", hooks={})
    _create_plugin(plugins_dir, "plugin-b", hooks={})

    for p in install_plugin.get_available_plugins():
        install_plugin.install_plugin(p)

    for p in install_plugin.get_available_plugins():
        install_plugin.remove_plugin(p)

    assert not (hooks_dir / "plugin-a.sh").exists()
    assert not (hooks_dir / "plugin-b.sh").exists()
