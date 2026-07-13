# Remove Proposit dependencies — implementation plan

## Capability changes

- **Updated:** `capabilities-sdlc` becomes usable by any repository or multi-repository workspace. Its file-location guidance, examples, planning gate, contradiction checks, and optional product-layer coordination no longer assume a particular product, repository layout, package scope, UI stack, or orchestrator repository.
- **Updated:** `/skill-cefailures:process-inbox-initiative` retains its multi-repository workflow but derives repository roles, capability locations, branch policy, ledgers, and coordination mechanisms from the host workspace instead of a fixed project topology.
- **No consuming-project migration:** this change generalizes the plugin itself. It does not move or rewrite capability documents in repositories that consume the plugin.

## Goal

Remove all active dependencies on and references to Proposit while preserving historical records. The result should work equally well in an unrelated single repository, monorepo, or coordinated multi-repository workspace and should remain compatible with both Claude Code and Codex.

This is a focused decoupling change. It does not require implementing the broader status, sidecar, tracker, or file-layout expansion proposed by the historical `capabilities-sdlc` v2 design.

## Research findings

The active coupling is concentrated in four surfaces:

| Surface | Finding | Required treatment |
|---|---|---|
| `skills/capabilities-sdlc/` | The skill trigger, canonical paths, product layer, route guidance, status examples, and all four exemplars assume one product's server/mobile/orchestration layout. | Rewrite the skill around project-declared structure and neutral examples. |
| `commands/process-inbox-initiative.md` | The scope guard names specific repositories; capability commits assume a specific orchestration repo, `main` handoff, ledger layout, planning plugin, and agent messaging vocabulary. | Make host conventions explicit inputs or conditional behavior; preserve the generic initiative lifecycle. |
| `README.md` | The public skill catalog describes `capabilities-sdlc` as “Proposit-style.” | Describe the generalized contract and optional multi-repo behavior. |
| Broker tests | Identity, storage, and formatting tests use Proposit package/repository names as fixtures. Runtime broker code is already generic. | Replace fixtures with neutral names while preserving every behavior assertion. |

There is no branded dependency in the plugin manifests or broker runtime. The existing approved `docs/superpowers/specs/2026-05-19-capabilities-sdlc-v2-design.md` already identifies the need for project-agnostic capability guidance, but it is unimplemented and intentionally retains branded exemplars and migration notes. Keep that spec as history; do not import those branded rollout decisions into the active skill.

The open `docs/inbox/2026-06-16-claude-md-anti-volatility-rule.md` is still processable input, not archived history. Its underlying anti-volatility proposal is generic, but its motivation and test cases use project-specific names. Generalize those examples in place unless the request is implemented and archived as part of separate work before this plan runs.

## Historical-document boundary

References may remain unchanged only in these historical locations:

- `docs/plans/**`, including this plan
- `docs/superpowers/plans/**`
- `docs/superpowers/specs/**`
- versioned `docs/release-notes/v*.md`
- versioned `docs/changelogs/v*.md`
- `docs/inbox/.archive/**`

The following are active and are not exempt: `README.md`, `skills/**`, `commands/**`, `scripts/**`, `tests/**`, plugin manifests, `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, `docs/FOLLOWUPS.md`, and unarchived `docs/inbox/**` entries.

## Design rules

1. **Declare structure; do not guess a branded topology.** The capability skill may explain common layouts, but the consuming project's `AGENTS.md`/`CLAUDE.md` or existing filesystem determines the actual roots and documentation-sync globs.
2. **Make multi-repo features optional.** A local capability file must be useful without an orchestrator or product layer. Product-layer coordination applies only when the host project declares that layer.
3. **Describe roles, not product names or tool brands.** Use terms such as “workspace root,” “child repository,” “web application,” “mobile application,” and “shared package.” Describe agent messaging and planning through the mechanisms available in the current host.
4. **Use neutral fixtures to test syntax and behavior.** Example identities should prove scoped package names, case preservation, slash encoding, broadcasts, and multi-recipient formatting without borrowing names from a real consumer.
5. **Preserve behavior unless coupling requires a change.** This work should not redesign broker protocols, capability statuses, or inbox archiving semantics.

## Implementation plan

### 1. Generalize `capabilities-sdlc`

Rewrite `skills/capabilities-sdlc/SKILL.md` and its reference docs:

- Change the trigger and overview from a product-specific repo family to any project maintaining user-capability documents.
- Replace fixed server/mobile/orchestration paths with two supported discovery patterns: capability files co-located with code, or a project-declared centralized capability tree. Require the host project to document which pattern and roots it uses; do not mandate a migration between them.
- Make the shared product layer an optional multi-repository pattern. Define the coordination contract in terms of a workspace coordinator and repo-local agents, with an in-repo fallback when no coordinator exists.
- Rewrite route edge cases as framework-qualified examples (for example, Next.js-style route groups and dynamic segments), not as rules for a named server repository.
- Keep the planning gate, three current statuses, contradiction-detection rule, and same-repository reference behavior unless a generic wording change is necessary.
- Replace all four branded authentication exemplars with neutral examples. Use generic paths and product language while retaining coverage of a user route, API endpoint, cross-screen feature, and screen-local capability.
- Ensure examples do not rely on private package names, bespoke auth decisions, exact repo names, or a specific orchestrator directory.

Files in scope:

- `skills/capabilities-sdlc/SKILL.md`
- every file under `skills/capabilities-sdlc/docs/`

### 2. Generalize the initiative command

Update `commands/process-inbox-initiative.md` while preserving its capabilities-first, spec-review, implementation, and integration phases:

- Replace the named-repository scope guard with a role check based on whether the current agent is operating at the declared workspace root or inside a child repository.
- Discover affected repositories from the request, the workspace's repository registry/instructions, or user input; do not embed a repository list.
- Apply a product-layer pass, initiative ledger updates, and per-repo briefings only when the host workspace declares those artifacts. Explain the fallback when each artifact is absent.
- Follow the host repository's branch, commit, and handoff policy. Remove the unconditional `main` commit and named orchestration-repo assumptions.
- Refer to the capability skill's current taxonomy rather than duplicating product-era constraints where possible.
- Replace tool-specific agent verbs with portable descriptions that work in Claude Code and Codex, while retaining the one-durable-agent-per-repository budget.
- Keep `/skill-cefailures:process-inbox` archiving semantics unchanged.

### 3. Replace branded test fixtures

Change only test data in:

- `tests/test_broker_identity.py`
- `tests/test_broker_storage.py`
- `tests/test_broker_format.py`

Use neutral fixtures such as `@acme/shared`, `acme-api`, `acme-mobile`, and `Example-Org/example-core`. Preserve assertions for:

- scoped and unscoped package identities;
- SSH and HTTPS Git remote parsing;
- organization/repository case preservation;
- slash-to-underscore storage encoding;
- single-recipient, multi-recipient, `you`, and broadcast rendering.

No broker runtime change is expected. If fixture replacement reveals runtime behavior tied to the old names, add a focused regression test before changing runtime code.

### 4. Generalize active documentation and intake

- Update the `README.md` Skills entry for `capabilities-sdlc` and the initiative-command description if its generalized behavior needs clarification.
- Generalize the examples in `docs/inbox/2026-06-16-claude-md-anti-volatility-rule.md`, because unarchived inbox documents are active inputs. Do not change the proposal's underlying intent.
- Do not edit historical plans, specs, archived inbox entries, or versioned release documentation merely to remove the name.
- Check both `.claude-plugin/` and `.codex-plugin/` metadata for descriptions made inaccurate by the generalized behavior. They currently contain no branded text, so change them only if the public description needs clarification; keep both surfaces aligned.

### 5. Documentation Sync closeout

The planned work changes public plugin guidance and command behavior, so these triggers are expected to fire:

- Update `README.md` under `[Public-API]`.
- Add plain-language user-facing notes to `docs/release-notes/upcoming.md` under `[Public-API]`.
- Add the implementation's commit hash range and developer detail to `docs/changelogs/upcoming.md` under `[Any-Code-Change]`.
- Inspect `docs/FOLLOWUPS.md` under `[Any-Code-Change]`. Add an entry only if implementation leaves a concrete code-related follow-up; otherwise leave it unchanged.

Do not bump plugin versions during implementation unless the user selects a release option after the changes have settled. If a version is later cut, update `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `.codex-plugin/plugin.json` together. This generalization is significant feature work, so the project convention favors a minor bump.

## Verification

Run, in order:

1. `python -m pytest tests/ -v`
2. A case-insensitive repository scan for the brand name and its package/org forms.
3. Confirm every remaining match is under the historical allowlist above; an active-file match fails the work.
4. Search active skills and commands for indirect legacy topology terms: old repo role names, private package scopes, fixed orchestration paths, unconditional `main` handoffs, and tool-specific coordination verbs.
5. Read the rendered README catalog and all rewritten exemplars for internal consistency and Claude Code/Codex portability.
6. Run `git diff --check` and inspect the final diff for accidental edits to historical documents.

Suggested active-tree audit:

```bash
rg -n -i --hidden --glob '!.git/**' \
  --glob '!docs/plans/**' \
  --glob '!docs/superpowers/plans/**' \
  --glob '!docs/superpowers/specs/**' \
  --glob '!docs/release-notes/v*.md' \
  --glob '!docs/changelogs/v*.md' \
  --glob '!docs/inbox/.archive/**' \
  '(\bProposit\b|proposit[-_/]|@proposit|Proposit-App)' .
```

Expected result: no output.

## Acceptance criteria

- No active file contains a Proposit name, package scope, organization name, repository name, or path.
- `capabilities-sdlc` can be adopted without knowing any pre-existing repository names or layout.
- The initiative command works as guidance for an arbitrary multi-repository workspace and degrades clearly when optional product-layer, ledger, briefing, broker, or planning facilities are absent.
- Broker behavior and test coverage remain unchanged; only fixture vocabulary changes unless a tested hidden dependency is found.
- README, upcoming release notes, and upcoming changelog describe the generalized public behavior.
- Claude Code and Codex plugin surfaces remain aligned.
- Historical documents remain intact.
