# Follow-ups

Load this doc when the project uses the opt-in `docs/FOLLOWUPS.md` standing log **and** you're prepending a new entry, annotating an existing item as complete, or scanning for items overlapping the current task.

`docs/FOLLOWUPS.md` is a standing log of deferred work items from completed feature implementations. Unlike release notes and changelogs — which are time-windowed records of what shipped — this file *grows* when work is deferred and *shrinks* when that work is later completed.

**This file is opt-in.** Use it only when the project's `## Documentation Sync` section lists it. Don't create `docs/FOLLOWUPS.md` in a project that hasn't adopted it.

## Entry Format

Each entry follows this template:

```markdown
# Work Summary Title
Commit range: abc1234-def5678
Branch name: feat/some-new-feature
Added on: 2026-05-06

## Follow-up Items
- Item 1
- Item 2

## Additional Notes
- Anything else relevant but not an action item
```

- **Title** — Brief description of the work that produced these follow-ups.
- **Commit range** — Starting and ending short hashes for the relevant work, so readers can trace it back.
- **Branch name** — The feature branch the work was done on. **Use the original branch name even if it has been merged and deleted from the remote** — other machines and stale clones may still carry it.
- **Added on** — Calendar date the entry was added; `YYYY-MM-DD` recommended for sortability.

New entries go at the top of the file (most recent first).

## What Counts as a Follow-up

**Include** code-related deferred work:
- Post-migration cleanups (e.g., "remove deprecated `/v1/users` endpoint after confirming all clients moved to `/v2`")
- Hardening skipped for scope (e.g., "add authorization controls to the new analytics routes")
- Refactors that emerged mid-task but weren't in scope
- Test coverage gaps the implementation revealed
- Performance work pushed out

**Exclude** anything that depends on a person doing something out-of-band:
- Smoke tests by the user
- Manual QA passes
- Stakeholder reviews or approvals
- "Verify in staging"

Those belong elsewhere — a tracker, a Slack ping, the PR description. If the item already shipped, it goes in the changelog or release notes. FOLLOWUPS.md is only for code work that hasn't happened yet.

## Lifecycle

- **At the end of feature work**, ask: was anything deferred? If yes, prepend a new entry block. If nothing was deferred, leave the file alone — don't write empty entries.
- **When picking up new work**, scan FOLLOWUPS.md for items overlapping the task at hand. Sometimes the lowest-effort path is finishing something already half-planned.
- **When a follow-up item is completed**, do not delete the bullet — annotate it so the historical record is preserved and future readers don't mistake completed work for outstanding work. Strike through the item text and append a completion date:

  ```markdown
  ## Follow-up Items
  - ~~Remove deprecated `/v1/users` endpoint after migration~~ (completed 2026-05-10)
  - Add authorization controls to the new analytics routes
  ```

  Edit or annotate `## Additional Notes` similarly when a note becomes obsolete rather than deleting it outright.
- **Do not rotate this file on version cuts.** Unlike `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`, FOLLOWUPS.md is a standing log that spans versions — items are annotated as they complete, not rotated when a version is tagged.

## Recommended Documentation Sync Entries

Projects using this convention should include this entry in their CLAUDE.md `## Documentation Sync` section:

```markdown
- `docs/FOLLOWUPS.md` [Any-Code-Change] — Standing log of deferred follow-up items; prepend an entry (commit range, branch, date) when feature work leaves code-related TODOs; annotate items as completed (strikethrough + date) when finished — do not delete
```

The trigger fires on any code change because every change is an opportunity to either log new deferred work or annotate previously tracked items as complete. The file is only modified when there is something to add or annotate — silence is the right outcome when no items are deferred and none reached completion.
