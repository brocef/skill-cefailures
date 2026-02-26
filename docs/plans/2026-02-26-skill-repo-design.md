# Library Skill Repository — Design Document

## Purpose

A repository of Claude Code skills for specific libraries, plus tooling to easily create new skills from online documentation. Each library gets a single skill. Skills provide API/pattern knowledge and debugging/troubleshooting guidance.

## Repository Structure

```
skill-cefailures/
├── skills/                          # All generated skills
│   └── <library>/
│       ├── SKILL.md                 # Routing layer
│       └── docs/
│           └── <topic>.md           # Topical reference docs
├── scripts/
│   ├── create_skill.py              # Fetch URL → generate skill via Claude API
│   └── install_skill.py             # Symlink skills into ~/.claude/skills/
├── requirements.txt                 # anthropic, httpx
└── README.md
```

## SKILL.md Routing Layer Format

Each SKILL.md follows this structure:

- **Frontmatter**: `name` and `description` (triggering conditions only)
- **Overview**: One-liner describing the library
- **When to Use**: Bullet list of triggering scenarios
- **Reference**: Table of `docs/*.md` files with brief descriptions, so Claude knows which file to `Read` for the current task
- **Key Patterns**: 3-5 critical patterns/gotchas inlined so Claude always has them without reading reference docs

The SKILL.md is always loaded on skill invocation. Detailed reference docs in `docs/` are read on-demand.

## create_skill.py

**Usage:** `python scripts/create_skill.py --name knex --url "https://..."`

**Steps:**

1. Fetch markdown/text content from the provided URL
2. Send to Claude API to analyze: identify library purpose, major topic areas, key patterns/gotchas, common troubleshooting issues
3. Send to Claude API to split: generate topical reference documents, SKILL.md routing layer, and inline key patterns
4. Write `skills/<name>/SKILL.md` and `skills/<name>/docs/*.md`

**Configuration:**

- Requires `ANTHROPIC_API_KEY` environment variable
- Uses `claude-sonnet-4-6` by default (configurable via `--model`)
- Refuses to overwrite existing skill unless `--force` is passed
- Validates URL is reachable before making API calls

## install_skill.py

**Usage:**

- `python scripts/install_skill.py knex` — install single skill
- `python scripts/install_skill.py --all` — install all skills
- `python scripts/install_skill.py --remove knex` — uninstall skill

**Steps:**

1. Validate `skills/<name>/SKILL.md` exists
2. Ensure `~/.claude/skills/` exists
3. Create symlink: `~/.claude/skills/<name>` → `<repo>/skills/<name>`
4. Report result, warn on conflicts (skip unless `--force`)

Pure stdlib Python — no external dependencies.

## Dependencies

- `anthropic` — Claude API calls in create_skill.py
- `httpx` — URL fetching

## Decisions

- Skills are symlinked (not copied) so updates to the repo propagate automatically
- SKILL.md is a routing layer, not a full dump — keeps skill invocation fast and focused
- Reference docs are split by topic so Claude only reads what's relevant
- Script fetches from any URL (not tied to Context7 specifically)
- No tests, CI, or additional config in initial version
