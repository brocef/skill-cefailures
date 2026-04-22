import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from broker_format import (
    escape_content,
    unescape_content,
    format_message,
    parse_message,
    ParsedMessage,
)


def test_escape_newlines_and_backslashes() -> None:
    assert escape_content("hello\nworld") == "hello\\nworld"
    assert escape_content("a\\b") == "a\\\\b"
    assert escape_content("a\\nb") == "a\\\\nb"


def test_unescape_is_inverse() -> None:
    originals = ["plain", "two\nlines", "back\\slash", "mixed\\n\\\\\n"]
    for s in originals:
        assert unescape_content(escape_content(s)) == s


def test_format_single_recipient_omits_arrow() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="@proposit/shared",
        recipients=["proposit-server"],
        content="CI green",
        viewer="proposit-server",
    )
    assert line == "2026-04-22T17:30:00Z [@proposit/shared] CI green"


def test_format_multi_recipient_shows_arrow_with_you_alias() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="proposit-mobile",
        recipients=["@proposit/shared", "proposit-server"],
        content="bumped to 0.3.0",
        viewer="@proposit/shared",
    )
    assert line == "2026-04-22T17:30:00Z [proposit-mobile → you, proposit-server] bumped to 0.3.0"


def test_format_broadcast() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="@proposit/shared",
        recipients=["BROADCAST"],
        content="publishing now",
        viewer="proposit-server",
    )
    assert line == "2026-04-22T17:30:00Z [@proposit/shared → BROADCAST] publishing now"


def test_format_escapes_newlines_in_content() -> None:
    line = format_message(
        timestamp="2026-04-22T17:30:00Z",
        sender="a",
        recipients=["b"],
        content="line1\nline2",
        viewer="b",
    )
    assert "\n" not in line
    assert line.endswith("line1\\nline2")


def test_parse_single_recipient() -> None:
    parsed = parse_message("2026-04-22T17:30:00Z [alice] hi there", viewer="bob")
    assert parsed == ParsedMessage(
        timestamp="2026-04-22T17:30:00Z",
        sender="alice",
        recipients=["bob"],
        is_broadcast=False,
        content="hi there",
    )


def test_parse_multi_recipient_with_you() -> None:
    parsed = parse_message(
        "2026-04-22T17:30:00Z [mobile → you, server] bumped 0.3.0", viewer="shared"
    )
    assert parsed.sender == "mobile"
    assert parsed.recipients == ["shared", "server"]
    assert parsed.is_broadcast is False
    assert parsed.content == "bumped 0.3.0"


def test_parse_broadcast() -> None:
    parsed = parse_message(
        "2026-04-22T17:30:00Z [shared → BROADCAST] publishing now", viewer="mobile"
    )
    assert parsed.is_broadcast is True
    assert parsed.recipients == ["BROADCAST"]
    assert parsed.sender == "shared"


def test_parse_rejects_malformed() -> None:
    with pytest.raises(ValueError):
        parse_message("not a message line", viewer="x")


def test_parse_unescapes_content() -> None:
    parsed = parse_message("2026-04-22T17:30:00Z [a] line1\\nline2", viewer="b")
    assert parsed.content == "line1\nline2"
