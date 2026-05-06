---
name: typebox
description: Use when you need JSON Schema definitions that infer TypeScript types, or you need to validate/parse/transform external data at runtime in a TypeScript codebase.
---

# typebox

Runtime type system for building in-memory JSON Schema that statically infers to TypeScript types and supports runtime validation and transformation.

| Doc | Scope |
|-----|-------|
| `docs/type-builder-core.md` | Core schema construction: objects, arrays/tuples, unions/intersections, literals/enums, records, recursive types |
| `docs/type-transformations.md` | Pick/Omit/Partial/Required/KeyOf/Index, union filtering with Exclude/Extract |
| `docs/value-runtime.md` | Value module — validate, parse, create defaults, clone/equal, Convert/Clean/Default/Assert/Errors |
| `docs/compile-validators.md` | Compile module — JIT validators, references/context, nested validator composition |
| `docs/script-module.md` | Script — schemas from TypeScript-like syntax strings, mapped/utility types, Script modules |
| `docs/formats-refine-codec.md` | String format validation, custom refinements, bidirectional codecs for encode/decode |
| `docs/troubleshooting.md` | Pitfalls around Parse behavior, errors reporting, formats, compiled validators |
