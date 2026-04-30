import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_constants import ORCHESTRATOR_RE


def _matches(identity: str) -> bool:
    return bool(ORCHESTRATOR_RE.fullmatch(identity))


def test_namespaced_orchestrator_matches() -> None:
    assert _matches("@orchestrator/myorg")
    assert _matches("@orchestrator/team-frontend")
    assert _matches("@orchestrator/a")


def test_bare_orchestrator_does_not_match() -> None:
    assert not _matches("orchestrator")
    assert not _matches("@orchestrator")
    assert not _matches("@orchestrator/")


def test_invalid_chars_rejected() -> None:
    assert not _matches("@orchestrator/foo/bar")
    assert not _matches("@orchestrator/foo bar")
    assert not _matches("@orchestrator/foo\nbar")
    assert not _matches("@orchestrator/../etc")


def test_pure_dot_scope_rejected() -> None:
    assert not _matches("@orchestrator/.")
    assert not _matches("@orchestrator/..")
    assert not _matches("@orchestrator/...")


def test_leading_special_char_rejected() -> None:
    assert not _matches("@orchestrator/.foo")
    assert not _matches("@orchestrator/-foo")
    assert not _matches("@orchestrator/_foo")


def test_trailing_special_chars_allowed() -> None:
    assert _matches("@orchestrator/foo.")
    assert _matches("@orchestrator/foo-")
    assert _matches("@orchestrator/foo_")


def test_single_char_must_be_alnum() -> None:
    assert _matches("@orchestrator/a")
    assert _matches("@orchestrator/Z")
    assert _matches("@orchestrator/0")
    assert not _matches("@orchestrator/.")
    assert not _matches("@orchestrator/-")
    assert not _matches("@orchestrator/_")


def test_scope_length_boundary() -> None:
    assert _matches(f"@orchestrator/{'x' * 64}")
    assert not _matches(f"@orchestrator/{'x' * 65}")


def test_peer_identities_do_not_match() -> None:
    assert not _matches("alice")
    assert not _matches("@myorg/projectA")
    assert not _matches("projectA-server")
