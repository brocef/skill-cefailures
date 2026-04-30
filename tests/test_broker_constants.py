import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_constants import is_reserved


def test_human_is_reserved() -> None:
    assert is_reserved("human") is True


def test_broadcast_is_reserved() -> None:
    assert is_reserved("BROADCAST") is True


def test_bare_orchestrator_is_not_reserved() -> None:
    """v1.5.0: bare 'orchestrator' is no longer reserved; only namespaced forms are."""
    assert is_reserved("orchestrator") is False


def test_namespaced_orchestrator_is_reserved() -> None:
    assert is_reserved("@orchestrator/myorg") is True
    assert is_reserved("@orchestrator/team-frontend") is True
    assert is_reserved("@orchestrator/a") is True


def test_orchestrator_with_empty_scope_is_not_reserved() -> None:
    assert is_reserved("@orchestrator/") is False


def test_orchestrator_with_no_scope_is_not_reserved() -> None:
    assert is_reserved("@orchestrator") is False


def test_orchestrator_with_invalid_chars_is_not_reserved() -> None:
    assert is_reserved("@orchestrator/foo/bar") is False
    assert is_reserved("@orchestrator/foo bar") is False
    assert is_reserved("@orchestrator/foo\nbar") is False
    assert is_reserved("@orchestrator/../etc") is False


def test_orchestrator_with_scope_too_long_is_not_reserved() -> None:
    long_scope = "x" * 65
    assert is_reserved(f"@orchestrator/{long_scope}") is False


def test_orchestrator_with_scope_at_max_length_is_reserved() -> None:
    max_scope = "x" * 64
    assert is_reserved(f"@orchestrator/{max_scope}") is True


def test_peer_identities_are_not_reserved() -> None:
    assert is_reserved("alice") is False
    assert is_reserved("@myorg/projectA") is False
    assert is_reserved("projectA-server") is False
    assert is_reserved("Proposit-App/proposit-mobile") is False
