"""Tests for `broker follow` — push-based message consumer."""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer, start_server
from broker_client import BrokerClient


@pytest.fixture
def sock_path():
    """Unix socket path under /tmp to avoid macOS 104-char limit."""
    fd, path = tempfile.mkstemp(prefix="broker_", suffix=".sock", dir="/tmp")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


BROKER_CLI = str(Path(__file__).parent.parent / "scripts" / "broker_cli.py")


def test_follow_subcommand_parses_args():
    """Parser accepts all documented flags without error."""
    result = subprocess.run(
        [sys.executable, BROKER_CLI, "follow", "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "--identity" in result.stdout
    assert "--idle-timeout" in result.stdout
    assert "--timeout" in result.stdout
    assert "--count" in result.stdout
    assert "--include-system" in result.stdout
    assert "--format" in result.stdout
