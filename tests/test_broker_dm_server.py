import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_server import BrokerServer


def test_server_initializes_dm_storage(tmp_path: Path) -> None:
    server = BrokerServer(storage_dir=tmp_path / "conversations")
    assert server.inbox_log.base_dir == tmp_path / "inbox"
    assert server.outbox_log.base_dir == tmp_path / "outbox"
    assert server.cursors.base_dir == tmp_path / "cursors"
    assert server.registry.path == tmp_path / "identities.json"
