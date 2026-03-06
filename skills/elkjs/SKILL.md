---
name: elkjs
description: Use when working with elkjs for automatic graph layout, configuring ELK layout algorithms, building the ELK JSON graph format, or troubleshooting elkjs layout issues in a JavaScript/TypeScript codebase.
---

# elkjs

elkjs is the JavaScript port of the Eclipse Layout Kernel (ELK). It computes positions and dimensions for graph elements (nodes, edges, ports, labels) — it is not a rendering framework. The flagship algorithm is ELK Layered, suited for directed node-link diagrams with ports.

## When to Use

- Installing or importing elkjs in a JS/TS project
- Building ELK JSON graph structures for layout input
- Choosing which layout algorithm to use (layered, force, stress, mrtree, radial, box, etc.)
- Configuring layout options (spacing, direction, edge routing, port constraints, etc.)
- Setting up Web Workers for non-blocking layout
- Interpreting layout output (coordinates, bend points, edge sections)
- Debugging layout issues or unexpected graph positioning

## Reference

Read the relevant doc based on your task:

- **Installation & API** — `docs/getting-started.md` — npm install, ELK constructor, layout() API, Web Workers, TypeScript imports, logging/debugging
- **JSON Graph Format & Coordinates** — `docs/json-format.md` — Node/port/label/edge structure, extended edges, edge sections, coordinate system, ELK text format
- **Choosing a Layout Algorithm** — `docs/algorithm-selection.md` — All algorithms with IDs, descriptions, supported features, and when to use each one
- **Core Layout Options** — `docs/layout-options-core.md` — Complete reference of shared layout options: spacing, direction, edge routing, ports, node sizing, hierarchy, and more
- **ELK Layered Deep Dive** — `docs/elk-layered.md` — Comprehensive reference for the layered algorithm: all options organized by phase (cycle breaking, layering, crossing minimization, node placement, edge routing, compaction, wrapping)
- **Troubleshooting & Gotchas** — `docs/troubleshooting.md` — GWT transpilation issues, label sizing, coordinate interpretation, Web Worker setup, common option mistakes, FAQs

## Key Patterns

- Graph input uses ELK JSON: nodes need `id` + `width`/`height`, edges use `sources`/`targets` arrays (not `source`/`target`)
- Set `elk.algorithm` (e.g., `'elk.layered'`) on the root node's `layoutOptions`; always use the `elk.` prefix to avoid ambiguity with short suffixes
- `layout()` returns a Promise — the resolved graph has `x`, `y`, `width`, `height` added to nodes/ports/labels, and `sections` with bend points on edges
- Label dimensions (`width`/`height`) must be set manually — ELK does not estimate text size
- For non-blocking layout in browsers, pass `workerUrl: './elk-worker.min.js'` to the ELK constructor
