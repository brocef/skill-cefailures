# Upcoming

## Changed

- **The `documentation-sync` skill has moved to the TCW plugin.** It is no longer part of skill-cefailures. If you use it, install the TCW plugin — the skill is now `tcw:documentation-sync`, and it does everything the old one did.
- **The two documentation-sync commands moved with it**, under new names:
  - `/skill-cefailures:documentation-sync:setup` → `/tcw:tcw-docs-sync-setup`
  - `/skill-cefailures:documentation-sync:cut-version` → `/tcw:tcw-cut-version`

TCW's version is ahead of the one that was here — it adds guidance for projects that define their own documentation triggers, and a workflow for folding new work into a version you cut locally but never pushed.

One thing did not make the move: the guidance for writing `docs/FOLLOWUPS.md` entries. If you keep a follow-ups log, its format is now up to you.
