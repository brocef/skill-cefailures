---
name: typebox
description: Use when working with TypeBox schemas or TypeBox Value/Format/System/Script utilities for schema construction, transformation, validation, or data manipulation in TypeScript/JavaScript.
---

# typebox

TypeBox is a TypeScript-first library for building JSON Schema definitions and performing value operations like creation, validation, repair, diff/patch, hashing, cloning, and mutation.

## When to Use

- You need to define JSON Schema using TypeBox (Type.Object, Type.Number, Type.String, etc.)
- You need to transform existing TypeBox schemas (Required/Partial/Pick/KeyOf/Mapped/Intersect/Refine)
- You need to repair, clean, create, diff/patch, hash, clone, equal-check, or mutate runtime values using TypeBox Value utilities
- You need to generate schemas via Type.Script (including mapped type transformations or scaling patterns)
- You need to register or use custom string formats with TypeBox Format
- You need to adjust TypeBox system settings (e.g., make compositor properties enumerable)

## Reference

Read the relevant doc based on your task:

- **Getting Started and Core Type Construction** — `docs/getting-started-and-core-types.md` — Install TypeBox and build core schemas with constraints/metadata and TypeScript static inference.
- **Schema Transforms and Type Utilities** — `docs/schema-transforms-and-utilities.md` — Transform and derive schemas with Required/Partial/Pick/KeyOf/Mapped/Intersect/Refine and related options.
- **Type.Script: Constructing and Mapping Schemas** — `docs/type-script-schemas.md` — Use Type.Script to construct JSON Schema from TS-like strings and apply mapped-type transformations, including advanced patterns and options.
- **Value Operations: Create, Repair, Clean, Diff/Patch, Hash, Clone/Equal, Mutate, Codec** — `docs/value-operations.md` — Runtime utilities for creating and transforming values to match schemas, synchronizing structures, hashing, cloning, and preserving references during updates.
- **Formats, Record Types, and System Settings** — `docs/formats-records-and-settings.md` — Define dynamic-key dictionaries with Type.Record, register custom formats, and adjust global TypeBox settings.
- **Troubleshooting and Gotchas** — `docs/troubleshooting.md` — Common TypeBox errors and behavioral gotchas shown in the docs.

## Key Patterns

- Value.Repair + additionalProperties: false: Repair removes excess properties only when the object schema sets { additionalProperties: false }; otherwise excess properties are retained to avoid data loss.
- Value.Diff -> Value.Patch: Generate edit commands with Value.Diff(left, right) and apply them to a value with Value.Patch(left, edits) to produce the right shape.
- Value.Create ambiguous constraints: Value.Create(Type.String({ format: 'email' })) throws CreateError unless a default is provided to resolve the constraint.
- Type.Script for mapping/scaling: Use Type.Script with a context object ({ T }) to reference existing schemas and apply mapped-type transformations; break deep structures into smaller scripts to avoid TypeScript depth limits.
- Custom formats via Format.Set/Get: Register custom validators with Format.Set(name, fn) and then use Type.String({ format: name }) with Value.Check, or call the validator from Format.Get.
