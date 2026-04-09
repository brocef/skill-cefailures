import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import install_broker


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory."""
    return tmp_path


def test_install_writes_broker_entry(project_dir):
    """install_broker writes the mcpServers.broker entry to .mcp.json."""
    install_broker.install_broker(
        identity="core",
        project_dir=project_dir,
    )
    mcp_path = project_dir / ".mcp.json"
    assert mcp_path.exists()
    data = json.loads(mcp_path.read_text())
    broker = data["mcpServers"]["broker"]
    assert broker["type"] == "stdio"
    assert "--identity" in broker["args"]
    assert "core" in broker["args"]
    assert broker["args"][0].endswith("mcp_broker.py")


def test_install_preserves_existing_keys(project_dir):
    """install_broker does not clobber other entries in .mcp.json."""
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps({
        "mcpServers": {"other-server": {"command": "node"}},
    }))

    install_broker.install_broker(identity="core", project_dir=project_dir)

    data = json.loads(mcp_path.read_text())
    assert "other-server" in data["mcpServers"]
    assert "broker" in data["mcpServers"]


def test_install_overwrites_existing_broker(project_dir):
    """Re-running install with a different identity updates the entry."""
    install_broker.install_broker(identity="core", project_dir=project_dir)
    install_broker.install_broker(identity="server", project_dir=project_dir)

    mcp_path = project_dir / ".mcp.json"
    data = json.loads(mcp_path.read_text())
    assert "server" in data["mcpServers"]["broker"]["args"]


def test_install_with_storage_dir(project_dir):
    """--storage-dir is passed through to the broker args."""
    install_broker.install_broker(
        identity="core",
        project_dir=project_dir,
        storage_dir=Path("/custom/path"),
    )
    mcp_path = project_dir / ".mcp.json"
    data = json.loads(mcp_path.read_text())
    args = data["mcpServers"]["broker"]["args"]
    assert "--storage-dir" in args
    assert "/custom/path" in args


def test_remove_broker(project_dir):
    """remove_broker removes the broker entry from .mcp.json."""
    install_broker.install_broker(identity="core", project_dir=project_dir)
    install_broker.remove_broker(project_dir=project_dir)

    mcp_path = project_dir / ".mcp.json"
    data = json.loads(mcp_path.read_text())
    assert "broker" not in data["mcpServers"]


def test_remove_broker_no_entry(project_dir, capsys):
    """remove_broker handles missing broker entry gracefully."""
    mcp_path = project_dir / ".mcp.json"
    mcp_path.write_text(json.dumps({"mcpServers": {}}))

    install_broker.remove_broker(project_dir=project_dir)
    captured = capsys.readouterr()
    assert "not configured" in captured.err


def test_nonexistent_project_dir(tmp_path):
    """install_broker exits with error if project dir doesn't exist."""
    with pytest.raises(SystemExit):
        install_broker.install_broker(identity="core", project_dir=tmp_path / "nope")
