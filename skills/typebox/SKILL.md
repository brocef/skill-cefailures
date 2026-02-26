---
name: typebox
description: Use when you need JSON Schema definitions that infer TypeScript types, or you need to validate/parse/transform external data at runtime in a TypeScript codebase.
---

# typebox

TypeBox is a runtime type system for building in-memory JSON Schema that statically infers to TypeScript types and supports runtime validation and transformation.

## When to Use

- Defining API/request/response schemas with TypeScript static inference
- Runtime validation of unknown/external data (e.g., network, config, user input)
- High-performance validation by compiling schemas into JIT validators
- Generating defaults, cleaning extra fields, or coercing types during parsing
- Creating schemas from TypeScript-like syntax strings (Script) or using formats/custom formats
- Building complex schemas via composition (unions, intersections, recursive types, transforms)

## Reference

Read the relevant doc based on your task:

- **Type Builder (Type) — Core Schema Construction** — `docs/type-builder-core.md` — Build JSON Schema objects that infer TypeScript types; includes object, arrays/tuples, unions/intersections, literals/enums, records, and recursive types.
- **Type Transformations and Operations** — `docs/type-transformations.md` — Transform and query schemas: Pick/Omit/Partial/Required/KeyOf/Index and union filtering with Exclude/Extract.
- **Value Module — Runtime Validation and Transformation** — `docs/value-runtime.md` — Validate, parse (transform), create defaults, clone/equal, and perform Convert/Clean/Default/Assert/Errors operations.
- **Compile Module — High-Performance Validators** — `docs/compile-validators.md` — Compile schemas into optimized validators; includes references/context and nested validator composition.
- **Script — TypeScript Syntax to Schema** — `docs/script-module.md` — Create schemas from TypeScript-like syntax strings, with context, mapped types, utility types, and Script modules.
- **Formats, Refine, and Codec** — `docs/formats-refine-codec.md` — String format validation (built-in and custom), custom refinements with error messages, and bidirectional codecs for encode/decode.
- **Troubleshooting and Gotchas** — `docs/troubleshooting.md` — Common pitfalls around Parse behavior, errors reporting, formats, and compiled validator expectations.

## Key Patterns

- Static inference with Type.Static<typeof Schema>: derive TypeScript types from schemas to keep runtime and compile-time in sync
- Prefer Value.Parse for full validation + transformation: Parse runs Clone -> Default -> Convert -> Clean -> Assert
- Use Compile(...) to compile once and reuse: compiled validators expose the same operations (Check/Parse/Create/Clean/Errors) with better performance
- Use schema transformations (Pick/Omit/Partial/Required/KeyOf/Index/Exclude/Extract) to keep object and union variants consistent without duplicating definitions
- Extend validation via Format.Set (custom string formats) and Type.Refine/Type.Codec for domain-specific checks and encode/decode transformations
