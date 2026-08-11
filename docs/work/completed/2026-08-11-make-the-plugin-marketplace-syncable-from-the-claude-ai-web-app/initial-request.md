# Make the plugin marketplace syncable from the claude.ai web app

## Origin

GitHub issue [#3](https://github.com/brocef/skill-cefailures/issues/3), filed
2026-08-11 by @brocef.

> ### Environment
>
> - Plugin version: `1.17.0`
> - Surface: **plugin packaging** — `.claude-plugin/marketplace.json` and the repo layout (not a skill, command, or `create_skill.py`)
> - Agent: Claude Code on the web (<https://claude.ai/code>); the same failure is reported for the Claude Desktop plugin directory
> - OS / platform: macOS 26.5
>
> ### Steps to reproduce
>
> 1. Go to <https://claude.ai/code> → plugin directory → Add marketplace
> 2. Enter `brocef/skill-cefailures` (the full URL `https://github.com/brocef/skill-cefailures` behaves the same)
> 3. Sync
>
> ### Expected vs. actual
>
> - **Expected:** the marketplace syncs and `skill-cefailures` becomes installable, as it does from the CLI.
> - **Actual:**
>
>   > Marketplace sync failed. Check the repository URL and try again.
>
> **The CLI path is unaffected** — `claude plugin marketplace add brocef/skill-cefailures` succeeds. The web/desktop flow syncs server-side through a stricter validator that collapses every distinct rejection into that one generic string, so the error text says nothing about the actual cause. Related upstream context: [ponytail#582](https://github.com/DietrichGebert/ponytail/issues/582) (a `status: failed_content` rejection over a single undocumented hook field) and [claude-code#61271](https://github.com/anthropics/claude-code/issues/61271) (the generic string masking a specific server-side payload).
>
> ### Remediation
>
> **A fix was verified end-to-end on `brocef/TCW`**, which failed identically and now syncs from the web app. `skill-cefailures` has both of the same defects. Two changes were made together:
>
> **1. Remove the self-referential directory symlink.**
>
> `plugins/skill-cefailures → ..` (mode `120000`) — confirmed present on `main`. Because the plugin's `source` is `"./"`, the plugin root *contains itself*: `plugins/skill-cefailures/plugins/skill-cefailures/…` without end. Any component scan that follows symlinks recurses forever, and a server-side one cannot be configured around the way local tooling can.
>
> Replace it by addressing the plugin root-relatively in `.agents/plugins/marketplace.json`:
>
> ```diff
> -        "path": "./plugins/skill-cefailures"
> +        "path": "."
> ```
>
> Measured equivalent against `codex-cli 0.147.0` on the TCW repo: both layouts resolve to the repo root, install the same skills, and vendor an identical tree. The symlink only ever pointed where `"."` already points.
>
> **2. Fill in the marketplace metadata.**
>
> `.claude-plugin/marketplace.json` on `main` is missing every field that marketplaces which *do* sync from the web carry:
>
> ```jsonc
> {
>   "name": "skill-cefailures",
>   "description": "…",              // ← missing; the one thing `claude plugin validate .` warns about
>   "owner": {
>     "name": "Brian Cefali",
>     "email": "…"                   // ← missing
>   },
>   "plugins": [{
>     "name": "skill-cefailures",
>     "source": "./",
>     "description": "Claude Code skills for specific libraries and patterns",
>     "version": "1.17.0",
>     "author": { "name": "…", "email": "…" }   // ← missing
>   }]
> }
> ```
>
> ### Honest caveat about causation
>
> TCW changed **both** of the above in one pass, so which one actually satisfied the validator is unknown. Applying both is what has been verified. If you want the answer, `skill-cefailures` is the ideal place to get it — fix one, test, then the other.
>
> Worth noting what the TCW result *did* settle: an earlier hypothesis was that claude.ai resolves repositories owned by the signed-in user through a GitHub App that isn't installed, which would have meant nothing in either repo was at fault. `brocef/TCW` syncing after these changes rules that out — the cause was in the repository.
>
> ### Also worth fixing while in there (not implicated in the sync failure)
>
> - `.claude-plugin/plugin.json` has no `homepage` or `repository`, while its Codex twin `.codex-plugin/plugin.json` has both. Two manifests describing one artifact that disagree about where it lives.
> - `.agents/plugins/marketplace.json` has no `description` at either level.
> - **Do not** copy TCW's `"license": "Apache-2.0"` declaration — this repo has **no `LICENSE` file** (GitHub's license endpoint returns 404). Add a LICENSE first, or omit the field; declaring a license the repo does not carry is worse than declaring none.
>
> ### Suggested regression guard
>
> TCW added a test asserting the *class* rather than the instance — no tracked path is a symlink resolving to its own ancestor — by walking `git ls-files -s` for mode `120000` entries. Pinning `plugins/skill-cefailures` by name would only stop that exact path from returning.

## Product changes

## Technical changes

## Meta changes

## References

- [ponytail#582](https://github.com/DietrichGebert/ponytail/issues/582) — a
  server-side `failed_content` rejection over one undocumented field; evidence
  that the validator rejects on specifics the generic error never names.
- [claude-code#61271](https://github.com/anthropics/claude-code/issues/61271) —
  the generic sync-failure string masking a specific server-side payload; why
  this has to be diagnosed by bisecting the repo rather than by reading the error.
- `brocef/TCW` — the sibling repo where both fixes were applied together and
  web sync then succeeded; the only end-to-end verification that exists.
