#!/usr/bin/env python3
"""Cross-module constants for the DM broker."""

import re

BROADCAST = "BROADCAST"

# Static reserved names that match exactly. The orchestrator namespace is
# matched separately via _ORCHESTRATOR_RE because it's a pattern, not a literal.
RESERVED_IDENTITIES: frozenset[str] = frozenset({
    "human",
    "BROADCAST",
})

# Orchestrator identities are namespaced: @orchestrator/<scope> where scope
# matches [A-Za-z0-9._-]{1,64}. Bare 'orchestrator' is NOT reserved (v1.5.0
# breaking change). Empty scope, slashes inside scope, or other special chars
# do not match — those identities fall through to peer-mode.
_ORCHESTRATOR_RE = re.compile(r"^@orchestrator/[A-Za-z0-9._-]{1,64}$")


def is_reserved(identity: str) -> bool:
    """True if `identity` requires a token-gated connect.

    Reserved identities are: 'human', 'BROADCAST', and any identity matching
    the @orchestrator/<scope> pattern. Anything else is unprivileged.
    """
    if identity in RESERVED_IDENTITIES:
        return True
    return bool(_ORCHESTRATOR_RE.fullmatch(identity))
