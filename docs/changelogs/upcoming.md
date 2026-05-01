# Upcoming

## Fixed
- `broker whoami` (and identity resolution generally) no longer returns the wrong identity when a project sits under a monorepo root that pins itself with `.broker/config.json`. Previously the resolver walked up to `$HOME` looking for `.broker/config.json` *before* checking `package.json`, so from `/org/projectA` the orchestrator's `/org/.broker/config.json` (`@org`) shadowed the project's own `/org/projectA/package.json` (`@org/projectA`). Resolution now walks up checking both files at each level; the closest source wins, with same-dir ties still going to `.broker/config.json` (preserving the explicit-pin semantic). Behavior at the orchestrator root is unchanged because there's no nearer `package.json` there.
