## Value.Create throws CreateError for ambiguous constraints

If you create a string with a `format` but no `default`, `Value.Create` cannot infer a valid value.

```typescript
import { Type, Value } from '@sinclair/typebox'

const T = Type.String({
  format: 'email'
})

const A = Value.Create(T)                            // throws CreateError
```

Fix by providing a default:

```typescript
const T = Type.String({
  format: 'email',
  default: 'user@domain.com'
})

const A = Value.Create(T)                            // const A: string = 'user@domain.com'
```

## Value.Repair does not remove extra properties unless you opt in

By default, Repair retains excess properties to avoid data loss. To remove excess properties, set `additionalProperties: false` on the object schema.

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
}, { additionalProperties: false })

const C = Value.Repair(T, { x: 1, y: 2, z: 3 })     // const C = { x: 1, y: 2 }
```

## Value.Clean returns `unknown`

The docs note the output type is `unknown`, so it should be checked.

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

const R = Value.Clean(T, { x: 1, y: 2, z: 3 })        // const R = { x: 1, y: 2 }
```

## Diff/Patch require correctly formatted edit commands

`Value.Patch` expects the edits in the same format produced by `Value.Diff`.

```typescript
const L = { x: 1, y: 2, z: 3 }
const R = { y: 4, z: 5, w: 6 }

const E = Value.Diff(L, R)
const A = Value.Patch(L, E)                          // const A = { y: 4, z: 5, w: 6 }
```

## Script scaling: avoid TypeScript depth limits with deep structures

Break deep schemas into smaller scripts and compose them.

```typescript
const D = Type.Script(`{ e: 1 }`)                   // depth + 1
const C = Type.Script({ D }, `{ d: D }`)            // depth + 1
const B = Type.Script({ C }, `{ c: C }`)            // depth + 1
const A = Type.Script({ B }, `{ b: B }`)            // depth + 1

const T = Type.Script({ A }, `{ a: A }`)            // ok
```

## Value.Hash is for fast comparisons, not persistent storage

The docs note hashing is intended for fast comparisons and should not be relied upon for persistent storage.

```javascript
const A = Value.Hash({ x: 1, y: 2, z: 3 });
const B = Value.Hash({ x: 1, y: 4, z: 3 });
```