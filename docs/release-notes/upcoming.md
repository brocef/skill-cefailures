# Upcoming

## Skill structure

- All skill `SKILL.md` files have been streamlined to a brief overview plus a routing table; the frontmatter `description` field now acts as the skill's invocation criteria. Detailed reference content lives entirely under each skill's `docs/` directory.
- The `broker` skill's inline reference content moved into a new `docs/critical-rules.md`, an expanded `docs/patterns.md`, and updated `docs/setup.md` and `docs/usage.md`.

## Documentation Sync skill

- Skill content is now consolidated into a single `SKILL.md` so it loads in full whenever the skill is invoked, instead of being split across multiple sub-task files. Only `docs/setup.md` remains as an on-demand subskill, used when first wiring up a project.
- New version-management guidance covers ecosystem-agnostic version-bump rules (npm/pnpm/yarn, Cargo, Python, Go modules, Claude Code plugin manifests, custom) and the `upcoming.md` → `v{version}.md` rotation ritual, including a user-confirmation step before rotating.
- Implementation plans should now include explicit documentation-update tasks for any trigger expected to fire, instead of deferring doc work to a completion sweep.
- The `## Documentation Sync` section template now opens with a directive that loads the skill itself when the section is present in a project's CLAUDE.md.
- `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md` are now opt-in: they only apply if the project's CLAUDE.md `## Documentation Sync` section explicitly lists them.
- `Public-API` and `Public-{Name}-API` semantics clarified — named entries carve out their area from the generic `Public-API`, with explicit partition and fall-through rules.
- `Any-Code-Change` is now scoped to behavior-affecting changes; cosmetic-only edits (formatting, comments, lint autofixes) no longer fire it.
- Migration suggestions reframed as offers — never executed unilaterally.

## brain-style skill

- The `claude-md.md` reference is now opt-in. It loads only when the user explicitly requests a brain-style review or creation of a CLAUDE.md, not on every CLAUDE.md edit.
