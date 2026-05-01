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
