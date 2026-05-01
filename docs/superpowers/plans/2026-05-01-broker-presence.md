# Broker Presence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `broker follow` open a long-lived socket so `who` and `broker clients` accurately list agents listening for messages.

**Architecture:** Add a `mode: "follow" | "oneshot"` field to the broker's wire protocol. Server tracks two maps: `self.clients` (any open socket, drives existing push routing) and `self.followers` (presence registry, drives `who` output and the "one follower per identity" rule). Follow connections register in both; oneshots in `self.clients` only. `cmd_follow_inbox` opens a `BrokerClient` and holds it; on socket close it exits non-zero. Inbox delivery stays file-based — the socket is purely a presence beacon.

**Tech Stack:** Python 3, asyncio, threading, pytest, `asyncio.start_unix_server`/`open_unix_connection`.

---

## Spec

Source spec: `docs/superpowers/specs/2026-05-01-broker-presence-design.md`. Read it before starting.

## File map

**Source files modified:**
- `scripts/broker_client.py` — `BrokerClient.__init__` gains `mode`; `connect()` includes it in the connect message.
- `scripts/broker_server.py` — `self.followers` map; `connect()` accepts `mode`; reject-second-follower rule; `disconnect()` removes from both maps; `_handle_list_clients` returns `{live, offline}`; `_handle_client` reads `mode` from connect message.
- `scripts/broker_cli.py` — `ServerREPL.__init__` passes `mode="follow"`; REPL `who` handler renders new payload; `broker clients` subcommand renders new payload; `cmd_follow_inbox` opens a follow socket on a background thread.

**Tests modified or added (existing files):**
- `tests/test_broker_dm_server.py` — followers map, reject-second, list_clients payload, registry/case-folding in offline list.
- `tests/test_broker_repl.py` — REPL appears as live `(you)`; updated `who` rendering.
- `tests/test_broker_dm_cli.py` — `broker clients` subcommand against new payload; `broker follow` connects to server, exits on connect failure, exits on rejection, exits on server shutdown.
- `tests/test_broker_client.py` — `mode` is forwarded in the connect message.

**Docs modified:**
- `skills/broker/SKILL.md`
- `skills/broker/docs/setup.md`
- `skills/broker/docs/troubleshooting.md`
- `skills/broker/docs/usage.md`
- `docs/release-notes/upcoming.md`
- `docs/changelogs/upcoming.md`

---

## Task 1: Add `mode` field to `BrokerClient`

Foundational, no behavior change. `BrokerClient` learns to forward a `mode` field in its connect message; default keeps existing behavior.

**Files:**
- Modify: `scripts/broker_client.py`
- Test: `tests/test_broker_client.py`

- [ ] **Step 1: Write the failing test** in `tests/test_broker_client.py` (append to the file)

```python
@pytest.mark.asyncio
async def test_client_forwards_mode_field(tmp_path, sock_path):
    """BrokerClient.connect() includes the mode field in the connect message."""
    server = BrokerServer(root_dir=tmp_path)
    srv = await start_server(server, sock_path)
    seen_modes: list[str] = []

    # Wrap server.connect to capture the mode passed by the connect handler.
    real_connect = server.connect
    def spy(identity, send, mode="oneshot", token=None):
        seen_modes.append(mode)
        return real_connect(identity, send, mode=mode, token=token)
    server.connect = spy

    try:
        client = BrokerClient(identity="alice", sock_path=sock_path, mode="follow")
        await client.connect()
        await client.close()
    finally:
        srv.close()
        await srv.wait_closed()

    assert seen_modes == ["follow"]
```

- [ ] **Step 2: Run the test to verify it fails**

```
pytest tests/test_broker_client.py::test_client_forwards_mode_field -v
```

Expected: FAIL — `BrokerClient.__init__` does not accept `mode`, and `BrokerServer.connect` does not accept `mode` either.

- [ ] **Step 3: Add `mode` to `BrokerClient`**

In `scripts/broker_client.py`, change `__init__` and `connect()`:

```python
class BrokerClient:
    """Connects to the broker socket server and provides an async DM API."""

    def __init__(self, identity: str, sock_path: str, mode: str = "oneshot") -> None:
        self.identity = identity
        self.sock_path = sock_path
        self.mode = mode
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[str, asyncio.Future] = {}
        self._listener_task: asyncio.Task | None = None
        self.on_push: asyncio.Queue[dict] | None = None  # optional queue for live inbox_message pushes

    async def connect(self) -> None:
        """Connect to the broker socket server."""
        self._reader, self._writer = await asyncio.open_unix_connection(self.sock_path)
        self._listener_task = asyncio.create_task(self._listen())
        await self._request({"type": "connect", "identity": self.identity, "mode": self.mode})
```

- [ ] **Step 4: Add `mode` to `BrokerServer.connect` (accept-and-ignore)**

In `scripts/broker_server.py`, update the signature so the test from Step 1 doesn't fail at the spy. Behavior is unchanged for now:

```python
def connect(self, identity: str, send: Callable, mode: str = "oneshot", token: str | None = None) -> None:
    """Register a client connection.

    BROADCAST is reserved as the fan-out pseudo-recipient and cannot be claimed
    as an identity. All other identities — including @orchestrator/<scope> and
    `human` — are name-reservations only, not auth-gated. The agent-side authority
    hierarchy (see skills/broker/docs/authority.md) gives `user` and orchestrator
    identities high trust by convention, but the broker performs no authentication.
    """
    if identity == BROADCAST:
        raise ValueError("BROADCAST is reserved and cannot be claimed as an identity.")
    self.clients[identity] = send
    self.registry.touch(identity, now=self._timestamp(), wrote=False)
```

Also update the connect-message handler in `_handle_client` (around `broker_server.py:261`):

```python
if msg["type"] == "connect":
    req_identity = msg["identity"]
    req_mode = msg.get("mode", "oneshot")
    def send(m, w=writer):
        w.write(json.dumps(m).encode() + b"\n")
    try:
        server.connect(req_identity, send, mode=req_mode, token=msg.get("token"))
    except ValueError as exc:
        error = {"type": "error", "id": msg.get("id", ""), "message": str(exc)}
        writer.write(json.dumps(error).encode() + b"\n")
        await writer.drain()
        break
    identity = req_identity
    response = {"type": "response", "id": msg.get("id", ""), "data": {"status": "connected"}}
    writer.write(json.dumps(response).encode() + b"\n")
    await writer.drain()
```

- [ ] **Step 5: Run the test to verify it passes**

```
pytest tests/test_broker_client.py::test_client_forwards_mode_field -v
```

Expected: PASS.

- [ ] **Step 6: Run the full test suite to make sure nothing regressed**

```
pytest tests/ -v
```

Expected: all tests pass. Existing `BrokerClient(identity, sock_path)` calls still work because `mode` defaults to `"oneshot"`.

- [ ] **Step 7: Commit**

```bash
git add scripts/broker_client.py scripts/broker_server.py tests/test_broker_client.py
git commit -m "feat(broker): add mode field to connect protocol (no-op default)"
```

---

## Task 2: Add `self.followers` map and populate on `mode="follow"`

Adds the presence registry. Follow connections land in both maps; oneshots only in `self.clients`. Disconnect clears both. No reject rule yet (next task).

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_broker_dm_server.py`)

```python
def test_follow_connect_populates_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    assert "alice" in server.clients
    assert "alice" in server.followers
    assert "since" in server.followers["alice"]


def test_oneshot_connect_does_not_populate_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    assert "alice" in server.clients
    assert "alice" not in server.followers


def test_default_mode_is_oneshot(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None)
    assert "alice" in server.clients
    assert "alice" not in server.followers


def test_disconnect_removes_from_both_maps(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.disconnect("alice")
    assert "alice" not in server.clients
    assert "alice" not in server.followers
```

- [ ] **Step 2: Run them to verify they fail**

```
pytest tests/test_broker_dm_server.py::test_follow_connect_populates_followers tests/test_broker_dm_server.py::test_oneshot_connect_does_not_populate_followers tests/test_broker_dm_server.py::test_default_mode_is_oneshot tests/test_broker_dm_server.py::test_disconnect_removes_from_both_maps -v
```

Expected: all four fail — `BrokerServer` has no `followers` attribute.

- [ ] **Step 3: Add the followers map and update `connect`/`disconnect`**

In `scripts/broker_server.py`:

In `BrokerServer.__init__`, add the new attribute:

```python
def __init__(self, root_dir: Path, audit_hook: Callable[[str], None] | None = None) -> None:
    self.root_dir = root_dir
    self.clients: dict[str, Callable] = {}
    self.followers: dict[str, dict] = {}
    self.audit_hook = audit_hook  # called once per routed message with the formatted line
    self.inbox_log = InboxLog(root_dir / "inbox")
    self.outbox_log = OutboxLog(root_dir / "outbox")
    self.cursors = CursorStore(root_dir / "cursors")
    self.registry = IdentityRegistry(root_dir / "identities.json")
```

Update `connect` to populate `self.followers` when `mode="follow"`:

```python
def connect(self, identity: str, send: Callable, mode: str = "oneshot", token: str | None = None) -> None:
    """Register a client connection.

    BROADCAST is reserved as the fan-out pseudo-recipient and cannot be claimed
    as an identity. All other identities — including @orchestrator/<scope> and
    `human` — are name-reservations only, not auth-gated.

    `mode="follow"` also registers the identity in `self.followers` (presence registry).
    `mode="oneshot"` only updates `self.clients`.
    """
    if identity == BROADCAST:
        raise ValueError("BROADCAST is reserved and cannot be claimed as an identity.")
    self.clients[identity] = send
    if mode == "follow":
        self.followers[identity] = {"since": self._timestamp()}
    self.registry.touch(identity, now=self._timestamp(), wrote=False)
```

Update `disconnect` to clear both maps:

```python
def disconnect(self, identity: str) -> None:
    """Remove the client's push callback. Inbox state is unaffected."""
    self.clients.pop(identity, None)
    self.followers.pop(identity, None)
```

- [ ] **Step 4: Run the new tests to verify they pass**

```
pytest tests/test_broker_dm_server.py -k "follow_connect_populates or oneshot_connect_does_not or default_mode_is_oneshot or disconnect_removes_from_both" -v
```

Expected: all four PASS.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): track followers separately from clients"
```

---

## Task 3: Reject second follower for same identity

`mode="follow"` for an identity already in `self.followers` raises `ValueError`. Oneshot connects during an active follow are still allowed.

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_second_follower_rejected(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    with pytest.raises(ValueError, match="already has an active follower"):
        server.connect("alice", lambda m: None, mode="follow")


def test_oneshot_during_active_follow_allowed(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.connect("alice", lambda m: None, mode="oneshot")  # must not raise
    assert "alice" in server.followers  # follower slot intact
```

`pytest` and `Path` are already imported at the top of the file.

- [ ] **Step 2: Run them to verify they fail**

```
pytest tests/test_broker_dm_server.py::test_second_follower_rejected tests/test_broker_dm_server.py::test_oneshot_during_active_follow_allowed -v
```

Expected: `test_second_follower_rejected` FAILs (no rejection); `test_oneshot_during_active_follow_allowed` may pass already since the existing logic allows it. Confirm both behaviors.

- [ ] **Step 3: Implement the reject rule**

In `scripts/broker_server.py`, update `connect`:

```python
def connect(self, identity: str, send: Callable, mode: str = "oneshot", token: str | None = None) -> None:
    if identity == BROADCAST:
        raise ValueError("BROADCAST is reserved and cannot be claimed as an identity.")
    if mode == "follow" and identity in self.followers:
        raise ValueError(f"identity '{identity}' already has an active follower")
    self.clients[identity] = send
    if mode == "follow":
        self.followers[identity] = {"since": self._timestamp()}
    self.registry.touch(identity, now=self._timestamp(), wrote=False)
```

- [ ] **Step 4: Run both tests to verify they pass**

```
pytest tests/test_broker_dm_server.py::test_second_follower_rejected tests/test_broker_dm_server.py::test_oneshot_during_active_follow_allowed -v
```

Expected: both PASS.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): reject second follower for the same identity"
```

---

## Task 4: New `list_clients` payload (live + offline split)

`_handle_list_clients` returns `{live: [...], offline: [...]}`. `live` from `self.followers`. `offline` from `IdentityRegistry.all()` minus identities in `live`, computed case-insensitively. The REPL and CLI consumers will be updated in later tasks.

**Files:**
- Modify: `scripts/broker_server.py`
- Test: `tests/test_broker_dm_server.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_list_clients_live_only_followers(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="follow")
    server.connect("bob", lambda m: None, mode="oneshot")
    data = server._handle_list_clients("alice", {})
    live_ids = [e["identity"] for e in data["live"]]
    offline_ids = [e["identity"] for e in data["offline"]]
    assert live_ids == ["alice"]
    assert "bob" in offline_ids
    assert data["live"][0]["mode"] == "follow"
    assert "since" in data["live"][0]
    assert "alice" not in offline_ids


def test_list_clients_offline_uses_registry(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    server.disconnect("alice")
    data = server._handle_list_clients("system", {})
    offline_ids = [e["identity"] for e in data["offline"]]
    assert "alice" in offline_ids
    entry = next(e for e in data["offline"] if e["identity"] == "alice")
    assert "lastSeenAt" in entry


def test_list_clients_case_insensitive_difference(tmp_path: Path) -> None:
    """Follower 'Alice' (mixed case) must not appear in offline as 'alice'."""
    server = BrokerServer(root_dir=tmp_path)
    server.connect("alice", lambda m: None, mode="oneshot")
    server.disconnect("alice")
    server.connect("Alice", lambda m: None, mode="follow")
    data = server._handle_list_clients("system", {})
    live_ids = [e["identity"] for e in data["live"]]
    offline_ids = [e["identity"] for e in data["offline"]]
    assert "Alice" in live_ids
    # Despite registry holding 'alice' (lowercased key, canonical 'alice'), it must not be reported as offline.
    assert all(i.lower() != "alice" for i in offline_ids)


def test_list_clients_sorted_by_identity(tmp_path: Path) -> None:
    server = BrokerServer(root_dir=tmp_path)
    server.connect("zeta", lambda m: None, mode="follow")
    server.connect("alpha", lambda m: None, mode="follow")
    data = server._handle_list_clients("system", {})
    live_ids = [e["identity"] for e in data["live"]]
    assert live_ids == ["alpha", "zeta"]
```

- [ ] **Step 2: Run them to verify they fail**

```
pytest tests/test_broker_dm_server.py -k "list_clients" -v
```

Expected: all four FAIL — current implementation returns `{"clients": [...]}`.

- [ ] **Step 3: Implement the new payload**

In `scripts/broker_server.py`, replace `_handle_list_clients`:

```python
def _handle_list_clients(self, identity: str, msg: dict) -> dict:
    """Return live followers and offline registered identities.

    `live`: identities with an open follow socket (presence). Sorted by identity.
    `offline`: identities in the registry that are not currently live, computed
    case-insensitively against `self.followers` keys. Sorted by identity.
    """
    live = [
        {
            "identity": identity_str,
            "mode": "follow",
            "since": entry["since"],
        }
        for identity_str, entry in sorted(self.followers.items())
    ]
    live_keys_lower = {entry["identity"].lower() for entry in live}
    offline_entries: list[dict] = []
    for canonical in self.registry.all():
        if canonical.lower() in live_keys_lower:
            continue
        reg = self.registry.get(canonical) or {}
        out = {"identity": canonical}
        if "lastSeenAt" in reg:
            out["lastSeenAt"] = reg["lastSeenAt"]
        if "lastWriteAt" in reg:
            out["lastWriteAt"] = reg["lastWriteAt"]
        offline_entries.append(out)
    offline_entries.sort(key=lambda e: e["identity"])
    return {"live": live, "offline": offline_entries}
```

- [ ] **Step 4: Run the new tests to verify they pass**

```
pytest tests/test_broker_dm_server.py -k "list_clients" -v
```

Expected: all four PASS.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: pre-existing tests that read the old `{clients: [...]}` shape (REPL `who`, `broker clients` subcommand, possibly an existing CLI test) WILL FAIL here. That's intentional — Tasks 5, 6, and 7 fix each consumer in turn. Confirm the failures are confined to:

- `tests/test_broker_repl.py::test_who_lists_connected_identities`
- any `tests/test_broker_dm_cli.py` test that exercises `broker clients`

If failures appear elsewhere, stop and investigate — the change should not break the send/broadcast/read/history paths.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_server.py tests/test_broker_dm_server.py
git commit -m "feat(broker): list_clients returns live/offline split"
```

---

## Task 5: REPL connects with `mode="follow"` and renders the new payload

`ServerREPL` registers itself as a follower so it appears in `live (you)`. The `who` command renders `{live, offline}` from the new payload.

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_repl.py`

- [ ] **Step 1: Update the failing test from Task 4**

Replace `test_who_lists_connected_identities` in `tests/test_broker_repl.py` with:

```python
def test_who_lists_live_followers_with_self_marker(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("alice", lambda m: None, mode="follow")
    repl.server.connect("bob", lambda m: None, mode="follow")
    assert repl._dispatch("who") is True
    out = capsys.readouterr().out
    # REPL identity is "user" — it should appear as live with the (you) marker.
    assert "user" in out and "(you)" in out
    assert "alice" in out and "live" in out
    assert "bob" in out


def test_who_shows_offline_for_disconnected_identities(tmp_path: Path, capsys) -> None:
    repl = _make_repl(tmp_path)
    repl.server.connect("alice", lambda m: None, mode="oneshot")
    repl.server.disconnect("alice")
    assert repl._dispatch("who") is True
    out = capsys.readouterr().out
    assert "alice" in out and "offline" in out


def test_who_empty_message(tmp_path: Path, capsys) -> None:
    """If there are no live or offline identities besides 'user', who still shows the REPL itself.

    Empty-state message only fires when both lists are empty, which never happens
    while the REPL is running because the REPL itself is a follower.
    """
    server = BrokerServer(root_dir=tmp_path)
    # Manually drive _handle_list_clients without REPL initialization to test the empty case.
    data = server._handle_list_clients("system", {})
    assert data["live"] == []
    assert data["offline"] == []
```

(`BrokerServer` is already imported at the top of the file.)

- [ ] **Step 2: Run them to verify the first two fail**

```
pytest tests/test_broker_repl.py::test_who_lists_live_followers_with_self_marker tests/test_broker_repl.py::test_who_shows_offline_for_disconnected_identities tests/test_broker_repl.py::test_who_empty_message -v
```

Expected: first two FAIL (REPL is a oneshot, render is the old shape). Third passes (it just exercises the server).

- [ ] **Step 3: Update `ServerREPL` to register as a follower**

In `scripts/broker_cli.py`, update `ServerREPL.__init__`:

```python
def __init__(self, server: BrokerServer, identity: str) -> None:
    self.server = server
    self.identity = identity
    self._req_counter = 0
    self.server.connect(identity, self._on_push, mode="follow")
    self._emit_messages = False
    # Wire the audit hook so live messages can be tailed.
    self.server.audit_hook = self._audit
    self._lock = threading.Lock()
```

- [ ] **Step 4: Update the REPL `who` handler to render the new payload**

In `scripts/broker_cli.py`, replace the `if command == "who":` branch in `ServerREPL._dispatch`:

```python
if command == "who":
    data = self._request({"type": "list_clients"})
    live = data.get("live", [])
    offline = data.get("offline", [])
    if not live and not offline:
        print("  (no live followers, no registered identities)")
        return True
    for entry in live:
        marker = " (you)" if entry["identity"] == self.identity else ""
        print(f"  {entry['identity']}       live, since {entry['since']}{marker}")
    for entry in offline:
        last_seen = entry.get("lastSeenAt", "—")
        print(f"  {entry['identity']}       offline, last seen {last_seen}")
    return True
```

- [ ] **Step 5: Run the updated REPL tests**

```
pytest tests/test_broker_repl.py -v
```

Expected: all three new tests PASS. Other REPL tests should continue to pass.

- [ ] **Step 6: Run the full test suite**

```
pytest tests/ -v
```

Expected: REPL tests pass. CLI `broker clients` test (if any) still fails — Task 6 fixes it.

- [ ] **Step 7: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_repl.py
git commit -m "feat(broker): REPL registers as follower; who renders live/offline"
```

---

## Task 6: `broker clients` subcommand renders the new payload

The CLI's `broker clients` handler at `scripts/broker_cli.py:516-524` currently iterates `result.get("clients", [])`. Rewrite it against `{live, offline}`.

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_broker_dm_cli.py`)

```python
def test_broker_clients_subcommand_renders_live_and_offline(broker) -> None:
    env = broker["env"]
    # Trigger registry entries by sending a DM (oneshot connect on each side).
    subprocess.run(CLI + ["send", "--identity", "alice", "--to", "bob", "seed"],
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
```

- [ ] **Step 2: Run it to verify it fails**

```
pytest tests/test_broker_dm_cli.py::test_broker_clients_subcommand_renders_live_and_offline -v
```

Expected: FAIL — current handler iterates `result["clients"]` and prints nothing for the new shape.

- [ ] **Step 3: Rewrite the CLI handler**

In `scripts/broker_cli.py`, replace the `elif args.command == "clients":` branch (around line 516):

```python
elif args.command == "clients":
    identity = _resolve_identity(args.identity)
    try:
        result = asyncio.run(run_oneshot(args.socket, identity, "list_clients", {}))
    except (ValueError, ConnectionError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    live = result.get("live", [])
    offline = result.get("offline", [])
    if not live and not offline:
        print("(no live followers, no registered identities)")
    for entry in live:
        print(f"{entry['identity']}       live, since {entry['since']}")
    for entry in offline:
        last_seen = entry.get("lastSeenAt", "—")
        print(f"{entry['identity']}       offline, last seen {last_seen}")
```

- [ ] **Step 4: Run the test to verify it passes**

```
pytest tests/test_broker_dm_cli.py::test_broker_clients_subcommand_renders_live_and_offline -v
```

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): clients subcommand renders live/offline output"
```

---

## Task 7: Socketed `cmd_follow_inbox`

`broker follow` opens a `BrokerClient` with `mode="follow"` and holds it. An asyncio loop on a background `threading.Thread` runs the client's `_listen` coroutine and sets a `threading.Event` when the socket closes (server shutdown / kill). The synchronous file-tail loop checks the event each iteration; when set, it prints `[broker] server disconnected` to stderr and returns non-zero.

If the initial connect fails (server unreachable), print the existing `Cannot connect to broker at … Is the broker server running?` message to stderr and return non-zero. If the server rejects the connect (already-active follower), print the rejection message to stderr and return non-zero.

**Files:**
- Modify: `scripts/broker_cli.py`
- Test: `tests/test_broker_dm_cli.py`

- [ ] **Step 1: Write the failing tests**

Add `import uuid` to the top of `tests/test_broker_dm_cli.py` (currently it's only imported inside the `broker` fixture). Then append:

```python
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
    # Wait briefly so the first follower has registered.
    time.sleep(0.5)
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
    time.sleep(0.5)  # let the follower establish its socket
    server_proc.terminate()
    server_proc.wait(timeout=3)
    rc = follow_proc.wait(timeout=5)
    assert rc != 0
    err = follow_proc.stderr.read().decode() if follow_proc.stderr else ""
    assert "server disconnected" in err.lower()
```

- [ ] **Step 2: Run them to verify they fail**

```
pytest tests/test_broker_dm_cli.py -k "follow_exits" -v
```

Expected: all three FAIL — `cmd_follow_inbox` doesn't open a socket; it just file-tails until the idle-timeout fires (returning 0).

- [ ] **Step 3: Rewrite `cmd_follow_inbox` to open a follow socket**

In `scripts/broker_cli.py`, replace `cmd_follow_inbox`:

```python
def cmd_follow_inbox(identity: str, idle_timeout: int, show_ids: bool) -> int:
    """Tail the per-identity DM inbox log and hold an open socket for presence.

    Delivery is file-based (the inbox log is the source of truth). The socket
    exists only as a presence beacon: server-side `who` reflects open follow
    connections. If the server stops or rejects the follow, this function exits
    non-zero.
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
            socket_closed.set()
            connected.set()  # release main thread to read the error
            return
        except ValueError as exc:
            connect_error["msg"] = str(exc)
            socket_closed.set()
            connected.set()
            return
        connected.set()
        try:
            # Hold the socket open. _listen runs in the background; when it exits
            # (server EOF), set socket_closed so the file-tail loop can stop.
            if client._listener_task is not None:
                await client._listener_task
        finally:
            socket_closed.set()
            await client.close()

    def thread_target() -> None:
        asyncio.run(run_socket())

    socket_thread = threading.Thread(target=thread_target, daemon=True)
    socket_thread.start()

    # Wait for the socket to either connect or fail.
    if not connected.wait(timeout=5):
        print(f"Cannot connect to broker at {sock_path} (handshake timeout). Is the broker server running?", file=sys.stderr)
        return 1
    if connect_error:
        print(connect_error["msg"], file=sys.stderr)
        return 1

    poll_interval = 0.2
    last_activity = time.monotonic()
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
            last_activity = time.monotonic()
        if idle_timeout > 0 and time.monotonic() - last_activity >= idle_timeout:
            return 0
        time.sleep(poll_interval)
```

- [ ] **Step 4: Run the new tests to verify they pass**

```
pytest tests/test_broker_dm_cli.py -k "follow_exits" -v
```

Expected: all three PASS.

- [ ] **Step 5: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/broker_cli.py tests/test_broker_dm_cli.py
git commit -m "feat(broker): follow opens a socket as a presence beacon"
```

---

## Task 8: Update broker skill docs

Documents the behavior change so users know `broker follow` now requires the server, and updates the output examples for `who` / `broker clients`.

**Files:**
- Modify: `skills/broker/SKILL.md`
- Modify: `skills/broker/docs/setup.md`
- Modify: `skills/broker/docs/troubleshooting.md`
- Modify: `skills/broker/docs/usage.md`

- [ ] **Step 1: Update `skills/broker/SKILL.md`**

Find the line in the Quick Reference table for `broker follow`:

```
| `broker follow [--idle-timeout N]` | Block, drain inbox, stream new DMs as they arrive |
```

Add a footnote / parenthetical: "Requires the broker server to be running — opens a socket so `who` lists the agent." Update the description directly:

```
| `broker follow [--idle-timeout N]` | Block, drain inbox, stream new DMs as they arrive (requires the server; opens a presence socket) |
```

- [ ] **Step 2: Update `skills/broker/docs/setup.md`**

Find the section that introduces the broker server (around the "Start the broker server" heading) and add a sentence: `broker follow` now requires the server; without it, follow exits with `Cannot connect to broker at ...`. Place this after the existing block that shows the `broker server` command.

- [ ] **Step 3: Update `skills/broker/docs/troubleshooting.md`**

The existing entry "`broker follow` exited with code 1 and 'socket closed unexpectedly'" needs revising. Replace its body with:

```
The server stopped or crashed mid-stream. With socketed follow, this is now the
expected exit path: when the broker server goes away, every active `broker follow`
exits non-zero so the agent learns that presence has dropped.

On restart, your inbox log and cursor persist — call `broker follow` again to
pick up where you left off. Any DMs sent while the server was down were rejected
at the sender (the sender will have seen the same Cannot-connect error), so
nothing is silently lost.
```

Add a new section after the "Identity mismatch" entry:

```
## "`broker follow` exited with 'identity X already has an active follower'"

Two `broker follow` processes resolved to the same identity (most often: two
terminals in the same workspace, since identity is derived from cwd). Only one
follower is allowed per identity at a time.

**Fix.** Stop one of them, or pin a different identity for one workspace via
`broker init --identity <other-name>`.
```

- [ ] **Step 4: Update `skills/broker/docs/usage.md`**

Find the section on the `who` REPL command (or the `broker clients` subcommand). Update the output example to show the new live/offline split:

```
broker> who
  alpha       live, since 2026-05-01T15:30:12Z
  user        live, since 2026-05-01T15:29:00Z (you)
  zeta        offline, last seen 2026-04-29T10:00:00Z
```

If the doc currently shows the old single-list format, replace it. Likewise update any `broker clients` output example.

- [ ] **Step 5: Verify no broken cross-references**

Run a quick text search to confirm no doc still describes `who` as showing only "currently connected clients" or describes follow as not requiring the server:

```
grep -RIn "currently connected" skills/broker/ docs/
grep -RIn "follow.*does not require\|works without the server" skills/broker/ docs/
```

Expected: no remaining stale references.

- [ ] **Step 6: Commit**

```bash
git add skills/broker/
git commit -m "docs(broker): document presence socket and live/offline who output"
```

---

## Task 9: Update release notes and changelog

Capture the wire-protocol change and the behavior change for the next version.

**Files:**
- Modify: `docs/release-notes/upcoming.md`
- Modify: `docs/changelogs/upcoming.md`

- [ ] **Step 1: Append to `docs/release-notes/upcoming.md`**

```markdown
# Upcoming

## Broker presence

`broker follow` now opens a long-lived socket to the broker server. The
`who` REPL command and the `broker clients` subcommand finally answer the
question they were named for: which agents are listening for messages right
now.

The output gains an `offline` section listing identities the broker has seen
before but that are not currently following.

**Behavior change:** `broker follow` requires the server to be running. If the
server stops, every active follow exits non-zero so the agent can learn its
presence has dropped.

**Foot-gun:** at most one follower is allowed per identity. Two terminals in
the same workspace will resolve to the same cwd-derived identity; the second
`broker follow` will be rejected with a clear error.
```

- [ ] **Step 2: Append to `docs/changelogs/upcoming.md`**

```markdown
# Upcoming

- feat(broker): `broker follow` opens a long-lived socket to the broker server
  for presence; inbox delivery remains file-based.
- feat(broker): `who` REPL command and `broker clients` subcommand return a
  `{live, offline}` payload listing live followers and registered-but-offline
  identities.
- feat(broker): server rejects a second `broker follow` for the same identity
  with `identity '<X>' already has an active follower`.
- feat(broker): wire protocol gains a `mode: "follow" | "oneshot"` field on the
  `connect` message; defaults to `oneshot` for backwards compatibility.
- breaking: `broker follow` now requires the broker server to be running.
- breaking: `list_clients` response changes from `{clients: [...]}` to
  `{live: [...], offline: [...]}`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/release-notes/upcoming.md docs/changelogs/upcoming.md
git commit -m "docs(release): note broker presence changes for upcoming release"
```

---

## Final verification

- [ ] **Run the full test suite one more time**

```
pytest tests/ -v
```

Expected: every test passes.

- [ ] **Manual smoke test**

In one terminal:

```
broker server
```

In a second terminal:

```
broker follow --identity alice --idle-timeout 60
```

In a third terminal:

```
broker clients --identity system
```

Expected output (something like):

```
alice       live, since 2026-05-01T15:30:12Z
<server identity>       live, since 2026-05-01T15:29:00Z
```

In the server REPL, run `who` — same shape, with `(you)` next to the server identity.

Stop the server (Ctrl-C). The `broker follow` process should exit non-zero with `[broker] server disconnected` on stderr.

Re-start the server, run `broker follow --identity alice` twice in different terminals — the second should fail with `identity 'alice' already has an active follower`.

If any of the smoke checks fail, do not consider the work done; the failure indicates a gap the test suite missed.
