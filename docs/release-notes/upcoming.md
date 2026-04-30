# Upcoming

## Broker

A new diagnostic, invoked by saying "check broker setup" or similar to Claude. It runs a quick 5-point health check on your local install — `~/.local/bin` on `$PATH`, broker symlink valid, server reachable, `Bash(broker:*)` permission active, version match between the installed broker and the latest cached plugin — then walks through fixes for any failures. Two remediations are user-action-required (PATH and starting the server); the rest Claude can apply with your confirmation.
