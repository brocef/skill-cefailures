# elkjs Skill Design

**Date:** 2026-03-06

## Goal

Create a Claude Code skill for elkjs — the JavaScript port of the Eclipse Layout Kernel — targeting web developers who use the `elkjs` npm package for automatic graph layout.

## Approach

Rather than using `create_skill.py` (which takes a single URL), the skill was written directly from scraped documentation across 15+ pages from `https://eclipse.dev/elk/documentation` and `https://eclipse.dev/elk/reference`, plus the elkjs GitHub README.

This approach was chosen because:
- Content spans many pages that need synthesis
- Java/Eclipse-specific content needed filtering for JS audience
- The complete option reference (318 options) needed organized coverage

## Skill Structure

| File | Purpose |
|------|---------|
| `SKILL.md` | Routing layer with triggers, reference table, key patterns |
| `docs/getting-started.md` | Installation, API, Web Workers, TypeScript, logging |
| `docs/json-format.md` | JSON graph format, coordinate system, ELK text format |
| `docs/algorithm-selection.md` | All 14 algorithms with IDs, descriptions, features, options |
| `docs/layout-options-core.md` | Shared layout options (spacing, ports, nodes, hierarchy, etc.) |
| `docs/elk-layered.md` | Complete ELK Layered reference organized by algorithm phase |
| `docs/troubleshooting.md` | GWT issues, label sizing, coordinates, FAQs |

## Sources

- `eclipse.dev/elk/documentation/tooldevelopers/*` — graph data structure, JSON format, coordinates, spacing, layout options
- `eclipse.dev/elk/reference/algorithms/*` — all algorithm reference pages
- `eclipse.dev/elk/reference/options.html` — complete 318-option list
- `github.com/kieler/elkjs` README — JS API, Web Workers, TypeScript usage, FAQs
