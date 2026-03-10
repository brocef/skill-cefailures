# Evaluating Triggers

## Trigger Reference

| Trigger | Fires When | Example |
|---------|-----------|---------|
| `Public-API` | Exported APIs, schemas, types, or public interfaces change | Renamed a function parameter, added a new export |
| `Public-{Name}-API` | Public interfaces change for a specific area of the codebase. `{Name}` is a descriptive label (not necessarily an exact folder path) that unambiguously identifies the area. | `Public-CLI-API` fires when CLI flags/behavior change; `Public-Auth-API` fires when auth endpoints change |
| `Any-Code-Change` | Any code change occurs, regardless of scope | Internal refactor, dependency bump, bugfix |
| `Only-Breaking` | Reverse-incompatible changes are introduced | Removed a parameter, changed return type, dropped support |

## How to Evaluate

For each file listed in the Documentation Sync section:

1. **Read the trigger** in brackets
2. **Assess your code changes** against the trigger definition
3. **If the trigger fires**, update the file according to its description
4. **If the trigger does NOT fire**, skip the file

Be precise: an internal refactor does NOT fire `Public-API`. A new optional parameter does NOT fire `Only-Breaking`. Match the trigger definition exactly.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping doc updates under time pressure | Triggers are objective — evaluate them regardless of urgency |
| Updating `[Public-API]` files for internal refactors | Internal changes don't fire `Public-API`. Check the trigger. |
| Treating `{Name}` in `Public-{Name}-API` as an exact path | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
