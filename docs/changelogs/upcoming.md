# Upcoming

<changes starting-hash="29787e8" ending-hash="HEAD">
- `skills/documentation-sync/SKILL.md`: changed the "When to offer a version cut" guidance. Agents now present a five-option choice list after a settled major change set: micro bump, minor bump, major bump, no bump with `upcoming.md` updates, or no bump with no documentation updates. Version-bump choices still route to `/skill-cefailures:documentation-sync:cut-version`.
- `commands/documentation-sync/cut-version.md`: clarified that a "Micro version bump" selection maps to `patch` in ecosystems that use patch/minor/major terminology.
- `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`: notes for this behavior change.
</changes>
