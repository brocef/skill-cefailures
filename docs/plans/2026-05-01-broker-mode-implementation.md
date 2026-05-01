# Broker Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `broker follow` with a one-shot `broker recv` batch receiver, ship a `/broker-mode` slash command, and rewrite the broker skill to make broker mode the canonical pattern.

**Architecture:** `cmd_recv_inbox` is a new function in `broker_cli.py`, modeled on the existing `cmd_follow_inbox` but with different exit semantics: it tracks `first_arrival_at` and exits when `burst_window` seconds elapse after that first arrival, rather than tracking `last_activity` and exiting on idle. Delivery mechanism (file-tail polling at 0.2s) and presence-socket lifetime (open for the duration of the call) are unchanged from `follow`. The protocol-level `mode="follow"` stays on the wire (server-side `self.followers` registry is unchanged); only the CLI subcommand renames. `broker follow` and its `--idle-timeout` flag are deleted in lockstep with the skill rewrite.

**Tech Stack:** Python 3, asyncio, Unix domain sockets, pytest. No new dependencies.

**Source:** Design at `docs/plans/2026-05-01-broker-mode-design.md`. Read it first.

---

## File structure

Files created in this release:

```
commands/broker-mode.md                              # NEW: slash command body
docs/release-notes/v1.6.0.md                         # NEW: release notes (rename of upcoming.md)
docs/changelogs/v1.6.0.md                            # NEW: changelog (rename of upcoming.md)
```

Files modified:

| File | Why |
|------|-----|
| `scripts/broker_cli.py` | Add `cmd_recv_inbox` + argparse `recv` subcommand; remove `cmd_follow_inbox` + `follow` subcommand. |
| `tests/test_broker_dm_cli.py` | Migrate `follow` tests to `recv`; add new tests per design §7. |
| `.claude-plugin/plugin.json` | Add `"commands": "./commands/"`; bump version to `1.6.0`. |
| `.claude-plugin/marketplace.json` | Bump version to `1.6.0`. |
| `skills/broker/SKILL.md` | Add Broker Mode section; rewrite Critical rules; update Quick Reference and frontmatter. |
| `skills/broker/docs/usage.md` | Replace `follow` reference with `recv`; clarify "live" semantic shift. |
| `skills/broker/docs/patterns.md` | Remove Monitor-streaming + standalone wait-for-reply; rewrite orchestrator section; add Broker Mode example. |
| `skills/broker/docs/troubleshooting.md` | Replace `follow` references; rewrite no-retry-on-restart entry. |
| `skills/broker/docs/setup.md` | Replace remaining `follow` references at lines 38, 71. |
| `docs/release-notes/upcoming.md` | Rename to `v1.6.0.md`; create fresh empty `upcoming.md`. |
| `docs/changelogs/upcoming.md` | Rename to `v1.6.0.md`; create fresh empty `upcoming.md`. |

Files explicitly **not** modified (called out in design §4):

- `skills/broker/docs/authority.md` — content unchanged.
- `skills/broker/docs/signals.md` — content unchanged.
- `skills/broker/docs/health-check.md` — content unchanged.
- `scripts/broker_server.py` — protocol and follower registry unchanged. The error message `"identity 'X' already has an active follower"` stays as-is; the troubleshooting doc explains it in terms of `recv`.

---

## Task list

- [ ] Phase 1: `broker recv` argparse + stub (Task 1)
- [ ] Phase 2: `broker recv` core behavior (Tasks 2–6)
- [ ] Phase 3: `broker recv` errors and presence (Tasks 7–11)
- [ ] Phase 4: Remove `broker follow` (Task 12)
- [ ] Phase 5: Slash command + plugin manifest (Tasks 13–14)
- [ ] Phase 6: Skill rewrites (Tasks 15–19)
- [ ] Phase 7: Release (Task 20)

---

## Phase 1: argparse skeleton

### Task 1: Add `recv` subcommand stub

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_broker_dm_cli.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_help_lists_subcommand tests/test_broker_dm_cli.py::test_recv_stub_exits_zero_on_empty_inbox -v`

Expected: FAIL with `argparse: invalid choice: 'recv'` (or similar — `recv` is not yet a subcommand).

- [ ] **Step 3: Add the argparse subcommand and dispatch stub**

In `scripts/broker_cli.py`, add a new `p_recv` block immediately after the existing `p_follow` block:

```python
    p_recv = subparsers.add_parser(
        "recv",
        help="Receive the next batch of inbox messages. Blocks for the first arrival, then drains follow-ups for --burst-window seconds.",
    )
    p_recv.add_argument("--identity", required=False, type=_validate_identity_arg,
                        help="Your identity (defaults to cwd-derived)")
    p_recv.add_argument("--timeout", type=int, default=0,
                        help="Max seconds to wait for the first message. 0 (default) waits indefinitely. Ignored if the inbox already has unread backlog at startup.")
    p_recv.add_argument("--burst-window", type=int, default=5,
                        help="Seconds to keep tailing for follow-ups after the first arrival. Default 5. 0 exits as soon as the first arrival has been delivered.")
    p_recv.add_argument("--show-ids", action="store_true",
                        help="Prefix each emitted line with the message ID.")
```

Add the dispatch case immediately after the existing `args.command == "follow"` case:

```python
    elif args.command == "recv":
        identity = _resolve_identity(args.identity)
        sys.exit(cmd_recv_inbox(identity, args.timeout, args.burst_window, args.show_ids))
```

Add the stub function above `cmd_follow_inbox`:

```python
def cmd_recv_inbox(
    identity: str,
    timeout: int,
    burst_window: int,
    show_ids: bool,
) -> int:
    """Receive the next batch of inbox messages. Stub — see Task 2 for behavior."""
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_help_lists_subcommand tests/test_broker_dm_cli.py::test_recv_stub_exits_zero_on_empty_inbox -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): add recv subcommand stub"
```

---

## Phase 2: `broker recv` core behavior

### Task 2: Empty inbox + timeout (basic loop)

**Files:**
- Modify: `scripts/broker_cli.py` (replace stub `cmd_recv_inbox` body)
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_broker_dm_cli.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_empty_inbox_with_timeout_exits_after_timeout -v`

Expected: FAIL — current stub exits immediately, so `elapsed` will be << 0.8s.

- [ ] **Step 3: Replace the stub with the basic loop**

Replace `cmd_recv_inbox` in `scripts/broker_cli.py` with:

```python
def cmd_recv_inbox(
    identity: str,
    timeout: int,
    burst_window: int,
    show_ids: bool,
) -> int:
    """Receive the next batch of inbox messages.

    Behavior:
    - If the inbox already has unread backlog at startup, emit it and start the
      burst window immediately, ignoring `timeout`.
    - Otherwise wait up to `timeout` seconds for the first arrival. If
      `timeout=0`, wait indefinitely. Exit cleanly (code 0) with empty stdout
      if the timer expires with no traffic.
    - On first arrival, continue tailing for `burst_window` seconds. New lines
      arriving within the window are emitted. Exit when the window expires.
    - `burst_window=0` exits as soon as the first arrival has been delivered;
      a multi-line backlog at startup is emitted in one go (no waiting between
      lines) before exit.
    - Cursor advances per inbox-read batch (matches today's `broker follow`).
    """
    import time
    import threading
    from broker_storage import InboxLog, CursorStore

    sock_path = os.environ.get("MCP_BROKER_SOCK", str(Path.home() / ".mcp-broker" / "broker.sock"))
    root_dir = Path(os.environ.get(
        "MCP_BROKER_ROOT", str(Path.home() / ".mcp-broker"),
    ))
    inbox = InboxLog(root_dir / "inbox")
    cursors = CursorStore(root_dir / "cursors")

    connected = threading.Event()
    socket_closed = threading.Event()
    connect_error: dict[str, str] = {}

    async def run_socket() -> None:
        client = BrokerClient(identity=identity, sock_path=sock_path, mode="follow")
        try:
            await client.connect()
        except (ConnectionRefusedError, FileNotFoundError):
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}. Is the broker server running?"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        except ValueError as exc:
            connect_error["msg"] = str(exc)
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        except Exception as exc:
            connect_error["msg"] = f"Cannot connect to broker at {sock_path}: {exc}"
            try:
                await client.close()
            except Exception:
                pass
            socket_closed.set()
            connected.set()
            return
        connected.set()
        try:
            if client._listener_task is not None:
                await client._listener_task
        finally:
            socket_closed.set()
            try:
                await client.close()
            except Exception:
                pass

    def thread_target() -> None:
        asyncio.run(run_socket())

    socket_thread = threading.Thread(target=thread_target, daemon=True)
    socket_thread.start()

    if not connected.wait(timeout=5):
        print(
            f"Cannot connect to broker at {sock_path} (handshake timeout). Is the broker server running?",
            file=sys.stderr,
        )
        return 1
    if connect_error:
        print(connect_error["msg"], file=sys.stderr)
        return 1

    poll_interval = 0.2
    start = time.monotonic()
    first_arrival_at: float | None = None

    while True:
        if socket_closed.is_set():
            print("[broker] server disconnected", file=sys.stderr)
            return 1
        offset = cursors.get(identity)
        lines, new_offset = inbox.read_from(identity, offset)
        if lines:
            for line in lines:
                print(_render_line(line, show_ids), flush=True)
            cursors.set(identity, new_offset)
            if first_arrival_at is None:
                first_arrival_at = time.monotonic()
                if burst_window == 0:
                    return 0

        now = time.monotonic()
        if first_arrival_at is None:
            if timeout > 0 and now - start >= timeout:
                return 0
        else:
            if now - first_arrival_at >= burst_window:
                return 0

        time.sleep(poll_interval)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_empty_inbox_with_timeout_exits_after_timeout -v`

Expected: PASS.

Also re-run the Task 1 stub tests to make sure they still pass:

```bash
python -m pytest tests/test_broker_dm_cli.py::test_recv_help_lists_subcommand tests/test_broker_dm_cli.py::test_recv_stub_exits_zero_on_empty_inbox -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): recv waits for first arrival up to --timeout"
```

---

### Task 3: First-arrival burst-window

**Files:**
- Test: `tests/test_broker_dm_cli.py`

The implementation already supports this from Task 2. This task adds a behavioral test that catches a regression if anyone refactors the loop wrong.

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_emits_first_arrival_and_exits_after_burst_window -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv first-arrival + burst-window exit"
```

---

### Task 4: Backlog-at-startup short-circuit

**Files:**
- Test: `tests/test_broker_dm_cli.py`

Backlog-at-startup is already supported by the Task 2 implementation (the first inbox read picks up backlog and sets `first_arrival_at`, which makes the burst window the only exit condition). This task pins the short-circuit behavior with a test that fails if anyone makes `--timeout` block when backlog is present.

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_backlog_short_circuits_timeout(broker) -> None:
    """Backlog at startup → drain immediately, ignore --timeout, run burst window."""
    env = broker["env"]
    # Pre-populate two messages.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "first"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "second"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    t0 = time.monotonic()
    result = subprocess.run(
        # --timeout=10 would normally block 10 seconds on empty inbox; with
        # backlog it must short-circuit and exit ~ burst-window seconds.
        CLI + ["recv", "--identity", "bob", "--timeout", "10", "--burst-window", "1"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    elapsed = time.monotonic() - t0
    assert result.returncode == 0, result.stderr
    assert "first" in result.stdout
    assert "second" in result.stdout
    assert elapsed < 3.0, f"backlog must short-circuit --timeout 10, got {elapsed}s"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_backlog_short_circuits_timeout -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): pin recv backlog-at-startup short-circuit of --timeout"
```

---

### Task 5: `--burst-window 0` semantics

**Files:**
- Test: `tests/test_broker_dm_cli.py`

The Task 2 implementation handles `burst_window=0` via the `if burst_window == 0: return 0` line that fires immediately after `first_arrival_at` is set. This pins it.

- [ ] **Step 1: Write the tests**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_burst_window_zero_with_single_arrival(broker) -> None:
    """--burst-window=0 + a single arriving message → emit one line, exit."""
    env = broker["env"]
    proc = subprocess.Popen(
        CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "0"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "only msg"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    stdout, stderr = proc.communicate(timeout=3)
    assert proc.returncode == 0, stderr
    assert "only msg" in stdout, stderr


def test_recv_burst_window_zero_with_multiline_backlog(broker) -> None:
    """--burst-window=0 + multi-line backlog → emit ALL backlog in one go, then exit."""
    env = broker["env"]
    for i in range(3):
        subprocess.run(
            CLI + ["send", "--identity", "alice", "--to", "bob", f"msg-{i}"],
            env=env, capture_output=True, text=True, timeout=3,
        )
    result = subprocess.run(
        CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "0"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    for i in range(3):
        assert f"msg-{i}" in result.stdout, f"missing msg-{i}: {result.stdout!r}"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_burst_window_zero_with_single_arrival tests/test_broker_dm_cli.py::test_recv_burst_window_zero_with_multiline_backlog -v`

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv --burst-window 0 with single arrival and multi-line backlog"
```

---

### Task 6: Burst-window hard cap

**Files:**
- Test: `tests/test_broker_dm_cli.py`

Verifies that messages arriving past the burst-window cap stay in the backlog and a second `broker recv` picks them up.

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_burst_window_is_a_hard_cap(broker) -> None:
    """Messages arriving after the burst window stay in backlog for the next recv."""
    env = broker["env"]
    proc = subprocess.Popen(
        CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "1"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.3)
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "msg-in-window"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    # Wait long enough for the burst window to expire.
    time.sleep(1.5)
    # This message arrives AFTER recv has exited.
    subprocess.run(
        CLI + ["send", "--identity", "alice", "--to", "bob", "msg-after-window"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    stdout, stderr = proc.communicate(timeout=3)
    assert proc.returncode == 0, stderr
    assert "msg-in-window" in stdout, stderr
    assert "msg-after-window" not in stdout, "post-window message must NOT be in this batch"

    # Second recv must pick it up from backlog.
    result2 = subprocess.run(
        CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "0"],
        env=env, capture_output=True, text=True, timeout=5,
    )
    assert result2.returncode == 0, result2.stderr
    assert "msg-after-window" in result2.stdout
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_burst_window_is_a_hard_cap -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): pin recv burst-window hard-cap behavior"
```

---

## Phase 3: `broker recv` errors and presence

### Task 7: Connection refused / server unreachable

**Files:**
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_exits_when_server_unreachable(tmp_path: Path) -> None:
    """`broker recv` exits non-zero with a clear error when the socket doesn't exist."""
    sock = Path(f"/tmp/broker_recv_{uuid.uuid4().hex[:8]}.sock")  # never created
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    result = subprocess.run(
        CLI + ["recv", "--identity", "alice", "--timeout", "1"],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Cannot connect to broker" in result.stderr
```

- [ ] **Step 2: Run test to verify it passes**

The Task 2 implementation already handles this via the `connect_error` path. Run:

```bash
python -m pytest tests/test_broker_dm_cli.py::test_recv_exits_when_server_unreachable -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv server-unreachable exit path"
```

---

### Task 8: Server crash mid-recv

**Files:**
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_exits_when_server_shuts_down(tmp_path: Path) -> None:
    """When the broker server stops mid-recv, `broker recv` exits non-zero."""
    sock = Path(f"/tmp/broker_recv_shutdown_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }
    server_proc = subprocess.Popen(
        CLI + ["server"],
        env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
        recv_proc = subprocess.Popen(
            CLI + ["recv", "--identity", "alice", "--timeout", "30"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        _wait_for_live_follower(env, "alice")
        server_proc.terminate()
        rc = recv_proc.wait(timeout=5)
        assert rc != 0
        err = recv_proc.stderr.read() if recv_proc.stderr else ""
        assert "server disconnected" in err or "socket closed" in err.lower(), err
    finally:
        try:
            server_proc.terminate()
        except Exception:
            pass
        try:
            server_proc.wait(timeout=3)
        except Exception:
            pass
        if sock.exists():
            sock.unlink()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_exits_when_server_shuts_down -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv server-shutdown exit path"
```

---

### Task 9: Server restart between iterations

**Files:**
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_after_server_restart_fails_then_resumable(tmp_path: Path) -> None:
    """First recv succeeds; server stops + restarts; second recv (during the down
    window) exits non-zero. After the second server is up, recv works again."""
    sock = Path(f"/tmp/broker_recv_restart_{uuid.uuid4().hex[:8]}.sock")
    env = {
        "MCP_BROKER_SOCK": str(sock),
        "MCP_BROKER_ROOT": str(tmp_path),
        "PATH": Path(sys.executable).parent.as_posix(),
    }

    def start_server():
        proc = subprocess.Popen(
            CLI + ["server"],
            env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if sock.exists():
                return proc
            time.sleep(0.05)
        proc.terminate()
        raise RuntimeError("server did not start")

    server = start_server()
    try:
        # Pre-populate one message so first recv has work to do.
        subprocess.run(
            CLI + ["send", "--identity", "alice", "--to", "bob", "first"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        first = subprocess.run(
            CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "0"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert first.returncode == 0, first.stderr
        assert "first" in first.stdout

        # Stop the server. Recv called now must fail fast.
        server.terminate()
        server.wait(timeout=3)
        if sock.exists():
            sock.unlink()
        down = subprocess.run(
            CLI + ["recv", "--identity", "bob", "--timeout", "1"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert down.returncode != 0
        assert "Cannot connect to broker" in down.stderr

        # Restart, and recv works again.
        server = start_server()
        subprocess.run(
            CLI + ["send", "--identity", "alice", "--to", "bob", "second"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        second = subprocess.run(
            CLI + ["recv", "--identity", "bob", "--timeout", "5", "--burst-window", "0"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert second.returncode == 0, second.stderr
        assert "second" in second.stdout
    finally:
        try:
            server.terminate()
            server.wait(timeout=3)
        except Exception:
            pass
        if sock.exists():
            sock.unlink()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_after_server_restart_fails_then_resumable -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv across server-restart (no retry; resumable after)"
```

---

### Task 10: Identity uniqueness rejection (no cursor advance)

**Files:**
- Test: `tests/test_broker_dm_cli.py`

The server-side single-follower-per-identity rule (`broker_server.py:56`) is already in effect for `mode="follow"` connections. Since `cmd_recv_inbox` connects with `mode="follow"`, this carries over. The rejection happens during the connect handshake, before any inbox reading or cursor work — so no cursor advance occurs on rejection. This task pins both behaviors.

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_second_invocation_rejected_for_same_identity(broker) -> None:
    """A second `broker recv` for an identity already-receiving exits non-zero."""
    env = broker["env"]
    first = subprocess.Popen(
        CLI + ["recv", "--identity", "alice", "--timeout", "10", "--burst-window", "10"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for_live_follower(env, "alice")
        result = subprocess.run(
            CLI + ["recv", "--identity", "alice", "--timeout", "1"],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        combined = result.stderr + result.stdout
        assert "already has an active follower" in combined, combined
    finally:
        first.terminate()
        first.wait(timeout=5)


def test_recv_rejection_does_not_advance_cursor(broker) -> None:
    """A rejected recv must leave the cursor file untouched.

    Strategy: pre-drain the inbox, snapshot the cursors directory, start a
    long-burst holder, attempt a second recv (rejected). Because the inbox is
    empty, the holder has nothing to advance — any cursor change between
    snapshots must be the rejected recv's doing. The expected outcome is no
    change.
    """
    env = broker["env"]
    tmp = broker["tmp"]
    cursors_dir = tmp / "cursors"

    # Seed and drain so a cursor file exists in a known state.
    subprocess.run(
        CLI + ["send", "--identity", "bob", "--to", "alice", "seed"],
        env=env, capture_output=True, text=True, timeout=3,
    )
    drain = subprocess.run(
        CLI + ["recv", "--identity", "alice", "--burst-window", "0", "--timeout", "5"],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert drain.returncode == 0, drain.stderr
    assert "seed" in drain.stdout

    before = {
        p.name: p.read_bytes()
        for p in cursors_dir.iterdir() if p.is_file()
    }

    # Hold an active recv so the next attempt is rejected. Inbox is empty;
    # holder will not advance the cursor.
    holder = subprocess.Popen(
        CLI + ["recv", "--identity", "alice", "--timeout", "20", "--burst-window", "20"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for_live_follower(env, "alice")
        rejected = subprocess.run(
            CLI + ["recv", "--identity", "alice", "--timeout", "1"],
            env=env, capture_output=True, text=True, timeout=5,
        )
        assert rejected.returncode != 0
        combined = rejected.stderr + rejected.stdout
        assert "already has an active follower" in combined, combined

        after = {
            p.name: p.read_bytes()
            for p in cursors_dir.iterdir() if p.is_file()
        }
        assert before == after, f"cursors changed across rejection: {before} → {after}"
    finally:
        holder.terminate()
        holder.wait(timeout=5)
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_second_invocation_rejected_for_same_identity tests/test_broker_dm_cli.py::test_recv_rejection_does_not_advance_cursor -v`

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): cover recv identity-uniqueness rejection and no-cursor-advance"
```

---

### Task 11: Presence socket lifetime

**Files:**
- Test: `tests/test_broker_dm_cli.py`

Verifies that an identity is "live" while `broker recv` is running and "offline" between calls.

- [ ] **Step 1: Write the test**

Add to `tests/test_broker_dm_cli.py`:

```python
def test_recv_presence_socket_lifetime(broker) -> None:
    """Identity is 'live' during recv, 'offline' between calls."""
    env = broker["env"]
    # Pre-state: alice is not in any client list (registry knows nothing).
    proc = subprocess.Popen(
        CLI + ["recv", "--identity", "alice", "--timeout", "10", "--burst-window", "10"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        _wait_for_live_follower(env, "alice")
        clients = subprocess.run(
            CLI + ["clients", "--identity", "system"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        assert clients.returncode == 0, clients.stderr
        live_block = clients.stdout
        live_for_alice = [
            line for line in live_block.splitlines()
            if line.lstrip().startswith("alice") and "live" in line
        ]
        assert live_for_alice, f"alice not shown as live: {live_block!r}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # After recv exits, alice must be offline (or absent from live list).
    deadline = time.time() + 5
    while time.time() < deadline:
        clients = subprocess.run(
            CLI + ["clients", "--identity", "system"],
            env=env, capture_output=True, text=True, timeout=3,
        )
        live_for_alice = [
            line for line in clients.stdout.splitlines()
            if line.lstrip().startswith("alice") and "live" in line
        ]
        if not live_for_alice:
            return
        time.sleep(0.1)
    raise AssertionError(
        f"alice still shown as live after recv exited: {clients.stdout!r}"
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_broker_dm_cli.py::test_recv_presence_socket_lifetime -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_broker_dm_cli.py
git commit -m "test(broker): pin recv presence-socket lifetime (live during, offline between)"
```

---

## Phase 4: Remove `broker follow`

### Task 12: Delete `follow` subcommand and `cmd_follow_inbox`

**Files:**
- Modify: `scripts/broker_cli.py` — delete `cmd_follow_inbox` (lines ~226–322) and the `p_follow` argparse block (lines ~493–502) and the `args.command == "follow"` dispatch case (lines ~589–591).
- Modify: `tests/test_broker_dm_cli.py` — delete tests that exercise `broker follow` directly: `test_follow_tails_inbox_file`, `test_follow_exits_when_server_unreachable`, `test_follow_exits_when_second_follower_for_same_identity`, `test_follow_exits_when_server_shuts_down`, `test_follow_kill_minus_9_clears_server_followers`. (The recv equivalents from Phase 2 and 3 cover the same coverage. The kill-minus-9 test, if it exercises something specific to the server-side follower cleanup, can be migrated to a recv variant — read it before deleting and decide.)

- [ ] **Step 1: Read the existing follow tests to decide which to migrate vs. delete**

Run: `python -m pytest tests/test_broker_dm_cli.py -v -k follow --collect-only`

Expected: a list of follow-related tests. For each, decide:
- Already covered by a recv equivalent in Phase 2–3? → delete.
- Tests something not yet covered (e.g. SIGKILL cleanup of server followers)? → migrate to recv variant before deleting.

The likely outcome: `test_follow_kill_minus_9_clears_server_followers` should be migrated to `test_recv_kill_minus_9_clears_server_followers` (same body, but invoke `recv` and use a long `--burst-window`). The other four `test_follow_*` tests have direct recv equivalents already.

- [ ] **Step 2: Migrate `test_follow_kill_minus_9_clears_server_followers` to recv**

Open `tests/test_broker_dm_cli.py`, locate the follow version, and add a recv version. Adapt the SIGKILL-then-check-server-clearing flow to use `recv --timeout 60 --burst-window 60`.

- [ ] **Step 3: Delete `cmd_follow_inbox` and the `follow` argparse + dispatch in `scripts/broker_cli.py`**

Remove:
- The function `cmd_follow_inbox(...)` (~100 lines).
- The `p_follow = subparsers.add_parser(...)` block.
- The `elif args.command == "follow":` branch in main.

- [ ] **Step 4: Delete the obsolete follow tests in `tests/test_broker_dm_cli.py`**

Remove:
- `test_follow_tails_inbox_file`
- `test_follow_exits_when_server_unreachable`
- `test_follow_exits_when_second_follower_for_same_identity`
- `test_follow_exits_when_server_shuts_down`
- `test_follow_kill_minus_9_clears_server_followers` (after migrating)

- [ ] **Step 5: Run the full broker test suite**

Run: `python -m pytest tests/test_broker_dm_cli.py tests/test_broker_dm_server.py tests/test_broker_dm_e2e.py -v`

Expected: all green. No reference to `broker follow` should remain.

Run a sweep:

```bash
grep -rn "broker follow\|cmd_follow_inbox\|--idle-timeout\|test_follow" scripts/ tests/
```

Expected: empty output. If anything remains in `scripts/` or `tests/` (excluding any release-notes mentions), fix it.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker)!: remove follow subcommand and --idle-timeout (replaced by recv)"
```

---

## Phase 5: Slash command + plugin manifest

### Task 13: Create `commands/broker-mode.md`

**Files:**
- Create: `commands/broker-mode.md`

- [ ] **Step 1: Verify the directory does not yet exist**

Run: `ls /Users/brian/Projects/skill-cefailures/commands/ 2>/dev/null`

Expected: directory does not exist (or is empty).

- [ ] **Step 2: Create `commands/broker-mode.md` with the slash-command body**

Write the file with this exact content:

```markdown
---
description: Enter Broker Mode — explicit foreground read-execute-respond loop for inbox-driven agent work.
---

You are now operating in Broker Mode.

Invoke the `broker` skill (Skill tool) and follow its **Broker Mode** section.
Run the loop until the in-conversation user instructs you to stop, or until a
DM from the reserved `user` identity instructs you to exit.
```

- [ ] **Step 3: Commit**

```bash
git add commands/broker-mode.md
git commit -m "feat(broker): add /broker-mode slash command"
```

Note: the slash command will not be discoverable by Claude Code until Task 14 declares the `commands/` directory in `.claude-plugin/plugin.json`.

---

### Task 14: Update plugin manifest to declare `commands/`

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Read the current manifest**

Run: `cat .claude-plugin/plugin.json`

Expected: a JSON object with `name`, `version`, `description`, `author`, `keywords`, and `skills` keys.

- [ ] **Step 2: Add the `commands` key**

Edit `.claude-plugin/plugin.json` to add `"commands": "./commands/"` immediately after the `"skills": "./skills/"` line. Result:

```json
{
  "name": "skill-cefailures",
  "version": "1.5.2",
  "description": "Claude Code skills for specific libraries and patterns",
  "author": {
    "name": "Brian Cefali"
  },
  "keywords": ["brain-style", "broker", "documentation-sync", "elkjs", "ieee", "knex", "permissions-auditor", "typebox"],
  "skills": "./skills/",
  "commands": "./commands/"
}
```

(The `version` will be bumped in Task 20; leave it at `1.5.2` for now.)

- [ ] **Step 3: Verify the JSON parses**

Run: `python3 -c 'import json; json.load(open(".claude-plugin/plugin.json"))'`

Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore(plugin): declare commands/ directory in manifest"
```

---

## Phase 6: Skill rewrites

### Task 15: Update `skills/broker/SKILL.md`

**Files:**
- Modify: `skills/broker/SKILL.md`

The Broker Mode section is the new canonical pattern. The Quick Reference table loses `follow` and gains `recv`. Critical rule #1 changes. Frontmatter description gains a broker-mode mention.

- [ ] **Step 1: Update frontmatter description**

Replace the existing `description:` line in the frontmatter with:

```markdown
description: Use when collaborating with other agents, coordinating with other Claude Code instances, sending DMs between agents, or when the user asks you to talk to another agent. Use when you see references to the broker command, inboxes, or agent identities. Broker Mode (`/broker-mode`) is the canonical pattern for agents waiting on inbound work — explicit foreground read-execute-respond loop, one iteration per inbox batch.
```

- [ ] **Step 2: Update the Quick Reference table**

Replace the row:

```markdown
| `broker follow [--idle-timeout N]` | Block, drain inbox, stream new DMs as they arrive (requires the server; opens a presence socket) |
```

with:

```markdown
| `broker recv [--timeout N] [--burst-window M]` | Receive the next batch: wait for first arrival, drain follow-ups for `M` seconds (default 5), exit. Use inside Broker Mode. |
```

- [ ] **Step 3: Rewrite Critical rule #1**

Replace:

```markdown
1. **Use `broker follow` to wait for messages.** Do not write `while true; broker read; sleep N`. Follow drains + streams + exits on idle/timeout.
2. **Don't `broker read` before `broker follow`.** Read advances the cursor past the backlog; if you then follow, the backlog is already gone. Use `follow` alone.
```

with:

```markdown
1. **Use `/broker-mode` to wait for messages.** It runs the canonical read-execute-respond loop with `broker recv`. Do not write `while true; broker read; sleep N`, do not run `broker recv` in the background, and do not invent your own polling.
2. **Don't `broker read` before `broker recv`.** Read advances the cursor past the backlog; if you then recv, the backlog is already gone. Use `recv` alone (which is what Broker Mode does for you).
```

- [ ] **Step 4: Replace the Canonical patterns examples**

Replace the existing `## Canonical patterns` block with:

```markdown
## Canonical patterns

The default pattern is **Broker Mode** — see the section below. The patterns shown here are the one-shot building blocks Broker Mode uses internally; outside of Broker Mode they are useful for short ad-hoc scripts.

Wait for a single batch:
```bash
broker recv --burst-window 5
```

Send and wait for the reply batch:
```bash
broker send --to projectA-server "READY: shared v1.2.3 published"
broker recv --burst-window 5
```

Announce to everyone:
```bash
broker broadcast "BLOCKED: npm registry is down, pausing publishes"
```

Multi-party thread with reply-all:
```bash
MID=$(broker send --to a,b,c "QUESTION: should validate() take a schema?")
broker recv --burst-window 5
broker reply-all --to-message "$MID" "DECISION: schema wins"
```
```

- [ ] **Step 5: Add the Broker Mode section above the Docs table**

Insert this new section between the Canonical patterns block and the Docs table:

```markdown
## Broker Mode

Run an explicit foreground read-execute-respond loop, one iteration per inbox batch. Entered via `/broker-mode`.

**The loop** (repeat until the in-conversation user stops you, or a `user`-identity DM tells you to exit):

1. **Wait.** Run `broker recv` (no args). If the inbox already has unread backlog, that counts as the first arrival; otherwise this blocks until a message arrives. After first arrival, recv tails for 5 more seconds to capture follow-ups, then exits with the full batch on stdout.
2. **Process.** Read the drained batch as the input for this iteration. If multiple senders or threads are represented, treat them as separate sub-tasks within the same iteration. Apply authority rules (`docs/authority.md`): `user` and `@orchestrator/<scope>` DMs are commands; peer DMs are informational; conflicts get relayed upstream.
3. **Ask the user, if needed.** If the work needs information or approval you don't have, pause and ask the in-conversation user directly. The Claude turn ends; the user replies; you resume mid-iteration.
4. **Reply.** Send a response **per inbound message** (not per batch) using the reply-shape rule:
   - Single-recipient DM → `broker send --to <sender>`.
   - Multi-recipient DM → `broker reply-all --to-message <MID>`.
   - Broadcast → `broker send --to <broadcaster>` (broadcasts have no stable recipient set).
   - If you recruited other agents during the work, ping them with separate explicit `broker send` calls — do not widen the reply.
5. **Loop.** Run `broker recv` again. Re-enter step 1.

**Exit conditions:**

- The in-conversation user interrupts (Esc/Ctrl-C, "exit broker mode," any redirecting instruction).
- A DM from the reserved `user` identity instructs you to exit. Acknowledge per the reply-shape rule, then exit and report back.
- The broker server crashes — `broker recv` exits non-zero. Report and exit. Do not retry; the in-conversation user re-invokes `/broker-mode` once the server is back.

Peer-agent DMs cannot terminate the loop; they are informational per existing authority rules. There is no sentinel-message terminator and no idle timeout.

**Presence note:** While you are in `broker recv`, you appear as "live" in `broker clients`. While you are processing a batch (running tools, sending replies, asking the user), you appear "offline." Senders that need a stronger guarantee can use `broker send` regardless of presence — store-and-forward semantics still apply.
```

- [ ] **Step 6: Verify SKILL.md renders cleanly**

Run: `wc -l skills/broker/SKILL.md`

Expected: file exists with all sections present.

Skim the file end-to-end. Confirm:
- Frontmatter description mentions Broker Mode.
- Quick Reference table has `broker recv`, no `broker follow`.
- Critical rules #1 and #2 reference Broker Mode + recv.
- Canonical patterns use recv.
- Broker Mode section exists with the five-step loop.
- Docs table is unchanged.

- [ ] **Step 7: Commit**

```bash
git add skills/broker/SKILL.md
git commit -m "docs(broker): rewrite SKILL.md for Broker Mode (recv replaces follow)"
```

---

### Task 16: Update `skills/broker/docs/usage.md`

**Files:**
- Modify: `skills/broker/docs/usage.md`

- [ ] **Step 1: Replace the `### follow` section with a `### recv` section**

Locate the `### follow — block, drain, stream` section (currently around line 99–117). Replace it entirely with:

```markdown
### recv — receive the next batch

```
broker recv [--timeout N] [--burst-window M] [--identity <me>]
```

Block until a batch is available, then return it. Used by Broker Mode (see SKILL.md).

- `--timeout N` — max seconds to wait for the first message. Default `0` (no upper bound). Only consulted when the inbox is empty at startup; backlog at startup short-circuits this entirely.
- `--burst-window M` — seconds to keep tailing for follow-ups after the first arrival. Default `5`. Hard cap; does not extend on each new arrival. Setting `0` exits as soon as the first arrival has been delivered.
- `--identity X` — override the cwd-derived identity.

Exits cleanly (code 0) on timeout-with-no-traffic or burst-window completion. Non-zero on socket error or server-disconnect.

`broker recv` opens a presence socket for its full duration. While it is running, your identity is shown as "live" by `broker clients`; while you are processing the batch (between `recv` calls), you appear "offline." This is intended: presence reflects readiness to receive.

Example:
```bash
$ broker recv --burst-window 5
2026-04-22T10:15:03Z [projectA-server] READY: shared v1.2.3 published
2026-04-22T10:15:47Z [projectA-server → you, @myorg_projectB] QUESTION: who owns the migration?
```
```

- [ ] **Step 2: Update the `clients` section to clarify the "live" semantic**

Locate the `### clients` section. Update the prose paragraph that describes "Live identities hold an active socket connection" to add a one-line clarification immediately after that sentence:

> With Broker Mode, "live" means the agent is currently waiting in `broker recv`. Between iterations of the loop (while the agent is processing or replying), it is shown as "offline" — that is the expected behavior, not a failure.

- [ ] **Step 3: Verify**

Run: `grep -n "follow\|--idle-timeout" skills/broker/docs/usage.md`

Expected: empty output (no remaining `follow` or `--idle-timeout` references).

- [ ] **Step 4: Commit**

```bash
git add skills/broker/docs/usage.md
git commit -m "docs(broker): replace follow reference with recv; clarify clients 'live' semantic"
```

---

### Task 17: Update `skills/broker/docs/patterns.md`

**Files:**
- Modify: `skills/broker/docs/patterns.md`

- [ ] **Step 1: Remove the standalone "Wait for a reply" canonical**

Delete the `### Wait for a reply` section entirely. Inside Broker Mode the agent never writes that pattern by hand; outside Broker Mode the new `recv` reference in `usage.md` shows the same pattern as a one-liner.

- [ ] **Step 2: Remove the "Streaming into Claude Code's `Monitor` tool" section**

Delete that section entirely.

- [ ] **Step 3: Rewrite the "Orchestrator watching many agents" section**

Replace its body with:

```markdown
### Orchestrator watching many agents

An orchestrator runs Broker Mode just like any other agent. The `@orchestrator/<scope>` inbox is the union of every DM addressed to it — `send --to @orchestrator/<scope>`, `reply-all` threads that include it, and broadcasts. A single `broker recv` per iteration drains the next batch; the orchestrator decides which messages to relay or act on, and replies per the shape rule. There is no fan-in bookkeeping and no background streaming; the orchestrator is just an agent that relays rather than implements.
```

- [ ] **Step 4: Update the "Multi-party thread with reply-all" example**

Replace `broker follow --idle-timeout 180` with `broker recv --burst-window 5` in that section's code block.

- [ ] **Step 5: Add a Broker Mode pattern section at the top**

Insert this new section as the first canonical pattern (above "Wait for a reply / send and wait" if the latter survives):

```markdown
### Broker Mode (canonical)

The canonical pattern for agents waiting on inbound work. Entered via `/broker-mode`. See `SKILL.md`'s "Broker Mode" section for the full loop. One worked iteration:

```bash
# Step 1 — wait for a batch.
$ broker recv
2026-04-22T10:15:03Z [projectA-server] QUESTION: which schema version for v1.3?

# Step 2 — process. (Agent does work. May ask the in-conversation user.)

# Step 3 — reply per the shape rule. Single-recipient DM → send --to sender.
$ broker send --to projectA-server "DECISION: v1.3.0; shared exposes the type."
msg-e9d201

# Step 4 — loop.
$ broker recv
...
```
```

- [ ] **Step 6: Verify**

Run: `grep -n "follow\|Monitor" skills/broker/docs/patterns.md`

Expected: empty output (no remaining `follow` references; the Monitor section is gone).

- [ ] **Step 7: Commit**

```bash
git add skills/broker/docs/patterns.md
git commit -m "docs(broker): patterns.md — Broker Mode canonical; remove Monitor + standalone wait-for-reply"
```

---

### Task 18: Update `skills/broker/docs/troubleshooting.md`

**Files:**
- Modify: `skills/broker/docs/troubleshooting.md`

- [ ] **Step 1: Replace `follow` references with `recv` throughout**

Sweep every literal `broker follow` and `--idle-timeout` reference:
- The "I'm writing a `while true; broker read; sleep N` loop" section: change the recommended fix from `broker follow --idle-timeout 120` to `/broker-mode` (with a note that `broker recv` is the underlying primitive).
- The "I ran `broker read` then `broker follow`" section: rename throughout to `broker recv`.
- The "`broker follow` exited with 'identity X already has an active follower'" section: rename to `broker recv`. Keep the server-side error string verbatim ("already has an active follower") and add a one-line note that the `follower` wording reflects the unchanged internal protocol mode; the user-facing primitive is `broker recv`.
- The "socket closed unexpectedly" section: rename `broker follow` → `broker recv` in the example.

- [ ] **Step 2: Add a no-retry-on-restart note to "socket closed unexpectedly"**

After the existing prose explaining that the inbox log + cursor persist across restarts, add:

```markdown
**Broker Mode does not retry on connection failure.** If the server is restarting when `broker recv` is called, `recv` exits non-zero, the agent reports the failure, and the loop ends. The user re-invokes `/broker-mode` once `broker server` is back. This is a deliberate trade — explicit failure beats hidden retries that could mask real outages.
```

- [ ] **Step 3: Verify**

Run: `grep -n "broker follow\|--idle-timeout" skills/broker/docs/troubleshooting.md`

Expected: empty output.

- [ ] **Step 4: Commit**

```bash
git add skills/broker/docs/troubleshooting.md
git commit -m "docs(broker): troubleshooting.md — recv replaces follow; document no-retry contract"
```

---

### Task 19: Update `skills/broker/docs/setup.md`

**Files:**
- Modify: `skills/broker/docs/setup.md`

- [ ] **Step 1: Locate the live `follow` references**

Run: `grep -n "broker follow\|--idle-timeout" skills/broker/docs/setup.md`

Expected: at least the lines mentioned in design §4 (~38 and ~71). Read each line in context.

- [ ] **Step 2: Rewrite each reference**

For each match:
- "broker follow requires the server to be running" → "broker recv requires the server to be running".
- "use `broker follow` (it blocks and streams…)" → "use `broker recv` inside Broker Mode (it blocks for the next batch and exits when the batch is delivered)".

Adapt sentence flow to keep the prose readable; do not just substitute keywords if the surrounding text needs adjustment.

- [ ] **Step 3: Verify**

Run: `grep -n "broker follow\|--idle-timeout" skills/broker/docs/setup.md`

Expected: empty output.

- [ ] **Step 4: Final sweep across the whole skills/ tree**

Run: `grep -rn "broker follow\|--idle-timeout\|cmd_follow_inbox" skills/ commands/`

Expected: empty output. If anything remains, fix it before committing.

- [ ] **Step 5: Commit**

```bash
git add skills/broker/docs/setup.md
git commit -m "docs(broker): setup.md — replace remaining follow references with recv"
```

---

## Phase 7: Release

### Task 20: Bump version, rotate release notes, tag

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Rename: `docs/release-notes/upcoming.md` → `docs/release-notes/v1.6.0.md`
- Rename: `docs/changelogs/upcoming.md` → `docs/changelogs/v1.6.0.md`
- Create: fresh empty `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`

- [ ] **Step 1: Verify the current version**

Run: `python3 -c 'import json; print(json.load(open(".claude-plugin/plugin.json"))["version"])'`

Expected: `1.5.2`. The new version is `1.6.0` (minor bump per CLAUDE.md: new skill section + breaking CLI change).

- [ ] **Step 2: Bump `version` in both manifests**

In `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, change `"version": "1.5.2"` → `"version": "1.6.0"`.

Verify both files still parse:

```bash
python3 -c 'import json; json.load(open(".claude-plugin/plugin.json"))'
python3 -c 'import json; json.load(open(".claude-plugin/marketplace.json"))'
```

Expected: no output, exit code 0 for both.

- [ ] **Step 3: Read the current upcoming.md files**

Run: `cat docs/release-notes/upcoming.md`. Read the existing entries. They will be the basis for `v1.6.0.md`. Same for `docs/changelogs/upcoming.md`.

- [ ] **Step 4: Rename `upcoming.md` → `v1.6.0.md` and add Broker Mode entries**

For `docs/release-notes/`:

```bash
git mv docs/release-notes/upcoming.md docs/release-notes/v1.6.0.md
```

Open `docs/release-notes/v1.6.0.md` and prepend an entry summarizing the broker mode change. Match the style of prior release notes (`docs/release-notes/v1.5.2.md` for shape). Cover:
- New `/broker-mode` slash command and the canonical loop it runs.
- `broker recv` replaces `broker follow`. Breaking change: `--idle-timeout` is gone, replaced by `--timeout` + `--burst-window`.
- Skill rewrite: Broker Mode is the canonical pattern; Monitor-streaming and standalone wait-for-reply patterns are removed.
- Presence semantics: agents are "live" only while in `broker recv`.

For `docs/changelogs/`:

```bash
git mv docs/changelogs/upcoming.md docs/changelogs/v1.6.0.md
```

Open `docs/changelogs/v1.6.0.md` and prepend a terse changelog entry of the same change. Match the style of `docs/changelogs/v1.5.2.md`.

- [ ] **Step 5: Create fresh empty `upcoming.md` files**

```bash
cat > docs/release-notes/upcoming.md <<'EOF'
# Upcoming
EOF

cat > docs/changelogs/upcoming.md <<'EOF'
# Upcoming
EOF
```

(If the previous `upcoming.md` files had a different placeholder shape — header style, sections — match that shape instead.)

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest tests/ -v`

Expected: all green.

- [ ] **Step 7: Verify nothing references `follow` or `--idle-timeout` anywhere it shouldn't**

Run:

```bash
grep -rn "broker follow\|--idle-timeout\|cmd_follow_inbox" \
  scripts/ tests/ skills/ commands/ docs/release-notes/upcoming.md docs/changelogs/upcoming.md
```

Expected: empty output. Mentions in `docs/plans/*.md` and `docs/release-notes/v1.6.0.md` / `docs/changelogs/v1.6.0.md` are fine — those are historical/release-note artifacts.

- [ ] **Step 8: Commit and tag**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json \
        docs/release-notes/v1.6.0.md docs/release-notes/upcoming.md \
        docs/changelogs/v1.6.0.md docs/changelogs/upcoming.md
git commit -m "chore(release): cut v1.6.0 (Broker Mode; recv replaces follow)"
git tag v1.6.0
```

- [ ] **Step 9: Confirm the tag is in place**

Run: `git tag -l v1.6.0`

Expected: `v1.6.0`.

- [ ] **Step 10: Final manual smoke**

Start a broker server in one terminal: `broker server`.

In another terminal:

```bash
broker send --identity alice --to bob "hello bob"
broker recv --identity bob --burst-window 1
# Should print "[alice] hello bob" then exit ~1s later.

broker recv --identity bob --timeout 1
# Should exit cleanly (~1s) with empty stdout.
```

Verify both work as expected.

---

## Self-review checklist

Before declaring this plan complete, confirm:

- [ ] Every item in design §1 (the loop steps) is reflected in SKILL.md's Broker Mode section (Task 15, Step 5).
- [ ] Every flag in design §2 (`--timeout`, `--burst-window`, `--identity`) has tests in Phase 2 and is documented in `usage.md` (Task 16).
- [ ] Every test case in design §7 has a corresponding task:
  - Empty inbox + `--timeout=0` → Task 3 (timeout=0 is the default; covered by burst-window test).
  - Empty inbox + `--timeout=N` → Task 2.
  - Backlog + `--timeout=0` → covered by Task 4 (with `--timeout 10`).
  - Backlog + `--timeout=N` → Task 4.
  - `--burst-window 0` multi-line backlog → Task 5.
  - `--burst-window 0` single first arrival → Task 5.
  - Burst-window hard cap → Task 6.
  - Server crash mid-recv → Task 8.
  - Connection refused at recv start → Task 7.
  - Server restart between iterations → Task 9.
  - Identity uniqueness rejection → Task 10.
  - Rejected recv does not advance cursor → Task 10.
  - Presence socket lifetime → Task 11.
  - `user`-DM termination — covered by skill content (Task 15) but not unit-tested; design §7 acknowledged this as integration-level.
- [ ] Every file listed in design §4 (skill rewrites) has a task:
  - SKILL.md → Task 15.
  - patterns.md → Task 17.
  - usage.md → Task 16.
  - troubleshooting.md → Task 18.
  - setup.md → Task 19.
- [ ] Files explicitly marked "no change" in design §4 (`authority.md`, `signals.md`, `health-check.md`) are not touched.
- [ ] Version bump and release-note rotation are handled (Task 20) per CLAUDE.md conventions.
