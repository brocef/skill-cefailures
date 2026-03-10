# Changelog Format

## Commit Hash Ranges

When updating a changelog file (or any file whose description mentions commit hashes), wrap entries with the first and last commit hashes that introduced the changes:

```markdown
## Changes

<changes starting-hash="abc1234" ending-hash="def5678">
- Renamed `host` parameter to `hostname` in `createClient`
- Added optional `timeout` parameter to `createClient`
</changes>
```

Where `abc1234` is the first commit hash and `def5678` is the last commit hash of the changes being documented.

## Getting Commit Hashes

```bash
# Most recent commit
git rev-parse --short HEAD

# If multiple commits were made, get the range
git log --oneline -n <number_of_commits>
```

## When to Skip Hash Wrappers

Skip commit hash wrappers if:
- `git` is not installed or not available
- The current working directory is not a git repository
- The user has explicitly asked not to include commit references

In these cases, write the changelog entries without the `<changes>` wrappers.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgetting commit hashes in changelog | Run `git rev-parse --short HEAD` after committing |
