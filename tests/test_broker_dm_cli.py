import subprocess
import sys
import time
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


def test_send_with_token_for_reserved_identity(broker) -> None:
    """`broker send --token X --identity @orchestrator/test ...` works when the token file matches."""
    env = broker["env"]
    tokens_dir = broker["tmp"] / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    (tokens_dir / "@orchestrator_test.token").write_text("ok\n")

    result = subprocess.run(
        CLI + ["send", "--token", "ok", "--identity", "@orchestrator/test", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    inbox = broker["tmp"] / "inbox" / "alice.log"
    assert inbox.exists()
    assert "[@orchestrator/test]" in inbox.read_text()


def test_send_without_token_for_reserved_identity_fails_cleanly(broker) -> None:
    """Connecting as a reserved identity without a token returns a non-zero exit and a JSON error."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/test", "--to", "alice", "nope"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    # stderr should carry a structured error mentioning the reservation.
    assert "reserved" in result.stderr.lower()


def test_broker_token_env_var_is_used(broker) -> None:
    """If --token is omitted, BROKER_TOKEN from the environment is used."""
    env = dict(broker["env"])
    tokens_dir = broker["tmp"] / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    (tokens_dir / "@orchestrator_test.token").write_text("env-tok\n")
    env["BROKER_TOKEN"] = "env-tok"

    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/test", "--to", "alice", "from env"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "[@orchestrator/test]" in (broker["tmp"] / "inbox" / "alice.log").read_text()


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
    """Validator must not reject valid namespaced identities (this would have a token error,
    but the parse-time check should pass)."""
    env = broker["env"]
    result = subprocess.run(
        CLI + ["send", "--identity", "@orchestrator/test", "--to", "alice", "ping"],
        env=env, capture_output=True, text=True,
    )
    # No token file, so connect rejects — that's a runtime error, not an argparse error.
    assert result.returncode != 0
    # Make sure the failure is the reserved-identity rejection, not the validator.
    assert "scope" not in result.stderr.lower()
    assert "reserved" in result.stderr.lower()


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
