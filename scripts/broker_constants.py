#!/usr/bin/env python3
"""Cross-module constants for the DM broker."""

import re

BROADCAST = "BROADCAST"

# Orchestrator identities are namespaced: @orchestrator/<scope>. The pattern
# is enforced at argparse time to catch typos. The broker does not authenticate
# orchestrator identities — the regex is purely a typo guard. See
# skills/broker/docs/authority.md for the convention-based authority model.
ORCHESTRATOR_RE = re.compile(r"^@orchestrator/[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
