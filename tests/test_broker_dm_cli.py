import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
CLI = [sys.executable, str(SCRIPTS / "broker_cli.py")]


@pytest.fixture
def broker(tmp_path: Path):
    """Start a broker server against tmp_path and yield a dict of paths + env.

    Uses /tmp for the socket to avoid macOS AF_UNIX path-length limits.
    """
    import uuid
    sock = Path(f"/tmp/broker_dm_cli_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    proc = subprocess.Popen(CLI + ["server"], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        proc.terminate()
        raise RuntimeError("broker server did not start")
    yield {"env": env, "tmp": tmp_path, "sock": sock}
    proc.terminate()
    proc.wait(timeout=3)
    if sock.exists():
        sock.unlink()


def _wait_for_live_follower(env: dict, identity: str, deadline_seconds: float = 5.0) -> None:
    """Poll `broker clients` until `identity` appears in the live list, or raise on timeout."""
    deadline = time.monotonic() + deadline_seconds
    result = None
    while time.monotonic() < deadline:
        result = subprocess.run(
            CLI + ["clients", "--identity", "system"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith(identity) and "live" in line:
                    return
        time.sleep(0.05)
    last_output = result.stdout if result is not None else ""
    raise RuntimeError(
        f"identity '{identity}' did not appear as live within {deadline_seconds}s. "
        f"Last clients output: {last_output!r}"
    )


def test_send_dm_writes_to_recipient_inbox(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "hello bob"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    inbox = broker["tmp"] / "inbox" / "bob.log"
    assert inbox.exists(), f"inbox not created at {inbox}. Stderr: {result.stderr}"
    content = inbox.read_text()
    assert "[alice]" in content
    assert content.strip().endswith("hello bob")


def test_send_dm_multi_recipient(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "group ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (broker["tmp"] / "inbox" / "bob.log").exists()
    assert (broker["tmp"] / "inbox" / "carol.log").exists()


def test_broadcast_fans_out(broker) -> None:
    env = broker["env"]
    # Register alice and bob by each sending a DM to the other.
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "seed"], env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "bob", "--to", "alice", "seed"], env=env, capture_output=True, text=True)
    # Broadcast from alice.
    result = subprocess.run(CLI + ["broadcast", "--identity", "alice", "announcement"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    bob_inbox = (broker["tmp"] / "inbox" / "bob.log").read_text()
    assert "→ BROADCAST" in alice_inbox
    assert "→ BROADCAST" in bob_inbox


def test_reply_all_cli(broker) -> None:
    env = broker["env"]
    sent = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob,carol", "kickoff"],
        env=env, capture_output=True, text=True,
    )
    message_id = sent.stdout.strip()
    assert sent.returncode == 0 and message_id.startswith("msg-")

    result = subprocess.run(
        CLI + ["reply-all", "--identity", "bob", "--to-message", message_id, "responding"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    alice_inbox = (broker["tmp"] / "inbox" / "alice.log").read_text()
    carol_inbox = (broker["tmp"] / "inbox" / "carol.log").read_text()
    bob_inbox_path = broker["tmp"] / "inbox" / "bob.log"
    bob_inbox = bob_inbox_path.read_text() if bob_inbox_path.exists() else ""
    assert "responding" in alice_inbox
    assert "responding" in carol_inbox
    assert "responding" not in bob_inbox  # no self-echo


def test_history_cli(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "one"], env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "two"], env=env, capture_output=True, text=True)
    result = subprocess.run(CLI + ["history", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("one")
    assert lines[1].endswith("two")


def test_history_cli_sent_flag(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "sent one"], env=env, capture_output=True, text=True)
    result = subprocess.run(CLI + ["history", "--identity", "alice", "--sent"], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert "sent one" in result.stdout


def test_read_cli_inbox_mode(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "msg1"], env=env, capture_output=True, text=True)
    first = subprocess.run(CLI + ["read", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert "msg1" in first.stdout
    second = subprocess.run(CLI + ["read", "--identity", "bob"], env=env, capture_output=True, text=True)
    assert second.stdout.strip() == ""


def test_whoami_prints_derived_identity(tmp_path: Path) -> None:
    import json as _json
    (tmp_path / "package.json").write_text(_json.dumps({"name": "test-pkg"}))
    result = subprocess.run(
        CLI + ["whoami"],
        cwd=tmp_path,
        env={"PATH": Path(sys.executable).parent.as_posix()},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "test-pkg" in result.stdout
    assert str(tmp_path) in result.stdout


def test_room_subcommands_are_gone(broker) -> None:
    """The legacy room CLI surface must no longer parse — argparse should reject it."""
    env = broker["env"]
    for legacy in ("create", "join", "leave", "close", "members", "list", "repl"):
        result = subprocess.run(CLI + [legacy], env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower(), f"{legacy}: {result.stderr}"


def test_follow_tails_inbox_file(broker) -> None:
    env = broker["env"]
    # Pre-populate one message so follow has something to drain.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "backlog msg"],
        env=env, capture_output=True, text=True,
    )
    # Start follow in background. Short idle-timeout so it exits quickly.
    follow = subprocess.Popen(
        CLI + ["follow", "--identity", "bob", "--idle-timeout", "2"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)
    # Send a live message while follow is running.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "live msg"],
        env=env, capture_output=True, text=True,
    )
    stdout, stderr = follow.communicate(timeout=5)
    assert "backlog msg" in stdout, stderr
    assert "live msg" in stdout, stderr


def test_cli_rejects_bare_orchestrator_with_at_prefix(broker) -> None:
    """`--identity @orchestrator` (no scope) is rejected at parse time, not at connect."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "@orchestrator" in result.stderr
    assert "scope" in result.stderr.lower()


def test_cli_rejects_orchestrator_with_empty_scope(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "scope" in result.stderr.lower()


def test_cli_rejects_orchestrator_with_invalid_chars(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/foo bar", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_cli_accepts_well_formed_orchestrator_identity(broker) -> None:
    """The validator must not reject valid namespaced identities. After option 3,
    no token is required — the send simply succeeds."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/test", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    inbox = broker["tmp"] / "inbox" / "alice.log"
    assert inbox.exists()
    assert "[@orchestrator/test]" in inbox.read_text()


def test_cli_rejects_orchestrator_with_scope_too_long(broker) -> None:
    """Scope > 64 chars is rejected at parse time."""
    env = broker["env"]
    long_scope = "x" * 65
    result = subprocess.run(
        CLI + ["send", "--identity", f"@orchestrator/{long_scope}", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "scope" in result.stderr.lower()


def test_cli_passes_through_orchestrators_plural_as_peer(broker) -> None:
    """`@orchestrators/foo` (plural typo) is a valid peer identity, not a reserved one.
    The validator must NOT reject it. The send may fail for other reasons (no broker token, etc.)
    but the rejection should NOT mention 'scope' or 'reserved-prefix-shaped'."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrators/foo", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    # The send may succeed (peer mode). If it fails, it must not be due to validator.
    assert "scope" not in result.stderr.lower()
    assert "reserved-prefix-shaped" not in result.stderr.lower()


def test_read_without_show_ids_strips_mid_prefix(broker) -> None:
    """Default `read` output does NOT include the MID column."""
    env = broker["env"]
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "hello"],
        env=env, capture_output=True, text=True,
    )
    result = subprocess.run(
        CLI + ["read", "--identity", "bob"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "[alice]" in out
    assert "hello" in out
    assert "msg-" not in out  # MID column hidden by default


def test_read_with_show_ids_prepends_mid_column(broker) -> None:
    """`broker read --show-ids` prepends the message ID to each line."""
    env = broker["env"]
    sent = subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "hello"],
        env=env, capture_output=True, text=True,
    )
    msg_id = sent.stdout.strip()
    result = subprocess.run(
        CLI + ["read", "--identity", "bob", "--show-ids"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout.strip().splitlines()
    assert len(out) == 1
    assert out[0].startswith(msg_id)
    assert "[alice]" in out[0]
    assert "hello" in out[0]


def test_history_with_show_ids(broker) -> None:
    env = broker["env"]
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "first"],
                   env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "second"],
                   env=env, capture_output=True, text=True)
    result = subprocess.run(
        CLI + ["history", "--identity", "bob", "--show-ids"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.strip().splitlines() if l]
    assert len(lines) == 2
    for line in lines:
        assert line.startswith("msg-")


def test_render_line_legacy_line_with_show_ids_uses_em_dash() -> None:
    """Pre-v1.5.0 inbox lines (no MID prefix) render an em-dash placeholder when --show-ids is on."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from broker_cli import _render_line, MID_COLUMN_WIDTH

    legacy = "2026-04-30T12:00:00Z [alice] hi from before v1.5.0"
    result = _render_line(legacy, show_ids=True)
    assert result.startswith("—")
    # The em-dash plus padding must occupy MID_COLUMN_WIDTH chars before the gutter.
    assert legacy in result
    # Default-off: returns the legacy line unchanged.
    assert _render_line(legacy, show_ids=False) == legacy


def test_broker_init_creates_config_with_explicit_identity(broker, tmp_path) -> None:
    env = dict(broker["env"])
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    result = subprocess.run(
        CLI + ["init", "--identity", "@myorg/projectA"],
        env=env, cwd=workdir, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    cfg = workdir / ".broker" / "config.json"
    assert cfg.exists()
    import json as _json
    data = _json.loads(cfg.read_text())
    assert data["identity"] == "@myorg/projectA"


def test_broker_init_uses_cwd_identity_when_omitted(broker, tmp_path) -> None:
    env = dict(broker["env"])
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    (workdir / "package.json").write_text('{"name": "auto-derived"}')
    result = subprocess.run(
        CLI + ["init"],
        env=env, cwd=workdir, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    import json as _json
    data = _json.loads((workdir / ".broker" / "config.json").read_text())
    assert data["identity"] == "auto-derived"


def test_broker_init_idempotent_for_same_identity(broker, tmp_path) -> None:
    env = dict(broker["env"])
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    subprocess.run(CLI + ["init", "--identity", "alice"], env=env, cwd=workdir, capture_output=True, text=True)
    result = subprocess.run(
        CLI + ["init", "--identity", "alice"],
        env=env, cwd=workdir, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "no change" in result.stdout.lower() or "already" in result.stdout.lower()


def test_broker_init_rejects_invalid_orchestrator_identity(broker, tmp_path) -> None:
    env = dict(broker["env"])
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    result = subprocess.run(
        CLI + ["init", "--identity", "@orchestrator/foo bar"],
        env=env, cwd=workdir, capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_whoami_honors_BROKER_IDENTITY_env(tmp_path: Path) -> None:
    """`broker whoami` reports the env-var identity when BROKER_IDENTITY is set."""
    import json as _json
    (tmp_path / "package.json").write_text(_json.dumps({"name": "cwd-derived"}))
    env = {
        "BROKER_IDENTITY": "alice",
        "HOME": str(tmp_path.parent),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    result = subprocess.run(
        CLI + ["whoami"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "alice" in result.stdout
    assert "cwd-derived" not in result.stdout


def test_broker_clients_subcommand_renders_live_and_offline(broker) -> None:
    env = broker["env"]
    # Trigger registry entries by sending a DM (oneshot connect on each side).
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "seed"],
                   env=env, capture_output=True, text=True)
    subprocess.run(CLI + ["send", "--identity", "bob", "--to", "alice", "seed"],
                   env=env, capture_output=True, text=True)
    # Now query clients.
    result = subprocess.run(
        CLI + ["clients", "--identity", "system"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    # The server REPL identity is whatever was passed to `broker server`. The
    # broker fixture starts the server with default identity (cwd-derived). At
    # minimum, alice and bob should appear as offline (their oneshot send
    # touched the registry, then they disconnected).
    assert "alice" in out
    assert "bob" in out
    assert "offline" in out


def test_follow_exits_when_server_unreachable(tmp_path: Path) -> None:
    """`broker follow` exits non-zero with a clear error when the socket doesn't exist."""
    sock = Path(f"/tmp/broker_follow_{uuid.uuid4().hex[:8]}.sock")  # never created
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    result = subprocess.run(
        CLI + ["follow", "--identity", "alice", "--idle-timeout", "1"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode != 0
    assert "Cannot connect to broker" in result.stderr or "Cannot connect to broker" in result.stdout


def test_follow_exits_when_second_follower_for_same_identity(broker) -> None:
    """A second `broker follow` for an identity already followed exits non-zero."""
    env = broker["env"]
    first = subprocess.Popen(
        CLI + ["follow", "--identity", "alice", "--idle-timeout", "10"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    _wait_for_live_follower(env, "alice")
    try:
        second = subprocess.run(
            CLI + ["follow", "--identity", "alice", "--idle-timeout", "1"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert second.returncode != 0
        combined = (second.stdout + second.stderr).lower()
        assert "already has an active follower" in combined
    finally:
        first.terminate()
        first.wait(timeout=3)


def test_follow_exits_when_server_shuts_down(tmp_path: Path) -> None:
    """When the broker server stops mid-follow, `broker follow` exits non-zero."""
    sock = Path(f"/tmp/broker_follow_shutdown_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    server_proc = subprocess.Popen(
        CLI + ["server"], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        server_proc.terminate()
        raise RuntimeError("broker server did not start")

    follow_proc = subprocess.Popen(
        CLI + ["follow", "--identity", "alice", "--idle-timeout", "30"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    _wait_for_live_follower(env, "alice")
    server_proc.terminate()
    server_proc.wait(timeout=3)
    rc = follow_proc.wait(timeout=5)
    assert rc != 0
    err = follow_proc.stderr.read().decode() if follow_proc.stderr else ""
    assert "server disconnected" in err.lower()


def test_follow_kill_minus_9_clears_server_followers(broker) -> None:
    """When a follower is SIGKILL'd, the server's _handle_client finally must clear it from `live`."""
    env = broker["env"]
    follower = subprocess.Popen(
        CLI + ["follow", "--identity", "ghost", "--idle-timeout", "60"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    _wait_for_live_follower(env, "ghost")

    # SIGKILL — no chance for cleanup on the follower side.
    os.kill(follower.pid, signal.SIGKILL)
    follower.wait(timeout=3)

    # Server side: poll until 'ghost' is no longer live.
    deadline = time.monotonic() + 5.0
    result = None
    while time.monotonic() < deadline:
        result = subprocess.run(
            CLI + ["clients", "--identity", "system"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        ghost_live = any(
            line.startswith("ghost") and "live" in line
            for line in result.stdout.splitlines()
        )
        if not ghost_live:
            return
        time.sleep(0.1)
    last_output = result.stdout if result is not None else ""
    raise AssertionError(f"'ghost' still appeared as live 5s after SIGKILL. Output: {last_output!r}")


def test_recv_help_lists_subcommand(broker) -> None:
    env = broker["env"]
    result = subprocess.run(
        CLI + ["recv", "--help"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert "--timeout" in result.stdout
    assert "--burst-window" in result.stdout
    assert "--identity" in result.stdout


def test_recv_stub_exits_zero_on_empty_inbox(broker) -> None:
    """Sanity: with --timeout=1 and an empty inbox, recv exits cleanly."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["recv", "--identity", "alice", "--timeout", "1"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_recv_empty_inbox_with_timeout_exits_after_timeout(broker) -> None:
    """Empty inbox + --timeout=1 → blocks ~1 second then exits empty."""
    env = broker["env"]
    t0 = time.monotonic()
    result = subprocess.run(
        CLI + ["recv", "--identity", "alice", "--timeout", "1"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    elapsed = time.monotonic() - t0
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert 0.8 <= elapsed <= 2.5, f"recv should wait ~1s, got {elapsed}"


def test_follow_collides_with_server_identity(tmp_path: Path) -> None:
    """`broker follow` against the same identity the server REPL uses must be rejected."""
    sock = Path(f"/tmp/broker_follow_collide_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    server_proc = subprocess.Popen(
        CLI + ["server", "--identity", "shared"], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    deadline = time.time() + 3
    while time.time() < deadline:
        if sock.exists():
            break
        time.sleep(0.05)
    else:
        server_proc.terminate()
        raise RuntimeError("broker server did not start")

    try:
        result = subprocess.run(
            CLI + ["follow", "--identity", "shared", "--idle-timeout", "1"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode != 0
        combined = (result.stdout + result.stderr).lower()
        assert "already has an active follower" in combined
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=3)


def test_recv_emits_first_arrival_and_exits_after_burst_window(broker) -> None:
    """Send a message during recv; recv emits it and exits after the burst window."""
    env = broker["env"]
    proc = subprocess.Popen(
        CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "1"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    # Give recv a moment to start tailing.
    time.sleep(0.3)
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "live msg"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    stdout, stderr = proc.communicate(timeout=5)
    assert proc.returncode == 0, stderr
    assert "live msg" in stdout, stderr
