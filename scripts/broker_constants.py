#!/usr/bin/env python3
"""Cross-module constants for the DM broker."""

BROADCAST = "BROADCAST"

RESERVED_IDENTITIES: frozenset[str] = frozenset({
    "orchestrator",
    "human",
    "BROADCAST",
})
