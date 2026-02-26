## Value.Create and ambiguous constraints

Ambiguous constraint example (throws):

```typescript
import { Type, Value } from '@sinclair/typebox'

const T = Type.String({
  format: 'email'
})

const A = Value.Create(T)                            // throws CreateError
```

Resolve with a default:

```typescript
const T = Type.String({
  format: 'email',
  default: 'user@domain.com'
})

const A = Value.Create(T)                            // const A: string = 'user@domain.com'
```

## Value.Repair (conform value to schema)

Notes: If `additionalProperties: false` is set, excess properties will be removed. Otherwise, excess properties are retained to prevent data loss.

```typescript
import { Type, Value } from '@sinclair/typebox';

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
}, { additionalProperties: false });

// Example 1: Repairing null to match the schema
const A = Value.Repair(T, null);
// Expected output: { x: 0, y: 0 }

// Example 2: Repairing an object with missing properties
const B = Value.Repair(T, { x: 1 });
// Expected output: { x: 1, y: 0 }

// Example 3: Repairing an object with excess properties (additionalProperties: false)
const C = Value.Repair(T, { x: 1, y: 2, z: 3 });
// Expected output: { x: 1, y: 2 }

// Example 4: Repairing an object with type coercion
const D = Value.Repair(T, { x: true, y: '42' });
// Expected output: { x: 1, y: 42 }
```

(also shown in a shorter form)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
}, { additionalProperties: false })                 // Tip: Use additionalProperties: false if you want
                                                    // Repair to remove excess properties. By default,
                                                    // the Repair function retain excess properties to 
                                                    // avoid data loss.

// ...

const A = Value.Repair(T, null)                     // const A = { x: 0, y: 0 }

const B = Value.Repair(T, { x: 1 })                 // const B = { x: 1, y: 0 }

const C = Value.Repair(T, { x: 1, y: 2, z: 3 })     // const C = { x: 1, y: 2 }

const D = Value.Repair(T, { x: true, y: '42' })    // const D = { x: 1, y: 42 }
```

## Value.Clean (remove extra properties)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

const R = Value.Clean(T, { x: 1, y: 2, z: 3 })        // const R = { x: 1, y: 2 }
```

## Value.Diff (compute edit commands)

TypeScript:

```typescript
const L = { x: 1, y: 2, z: 3 }                       // Left
const R = { y: 4, z: 5, w: 6 }                       // Right

const E = Value.Diff(L, R)                           // const E = [
                                                     //   { type: 'update', path: '/y', value: 4 },
                                                     //   { type: 'update', path: '/z', value: 5 },
                                                     //   { type: 'insert', path: '/w', value: 6 },
                                                     //   { type: 'delete', path: '/x' }
                                                     // ]
```

JavaScript:

```javascript
const L = { x: 1, y: 2, z: 3 }                       // Left
    const R = { y: 4, z: 5, w: 6 }                       // Right
    
    const E = Value.Diff(L, R)                           // const E = [
                                                         //   { type: 'update', path: '/y', value: 4 },
                                                         //   { type: 'update', path: '/z', value: 5 },
                                                         //   { type: 'insert', path: '/w', value: 6 },
                                                         //   { type: 'delete', path: '/x' } 
                                                         // ]
```

## Value.Patch (apply edit commands)

TypeScript:

```typescript
const L = { x: 1, y: 2, z: 3 }                       // Left
const R = { y: 4, z: 5, w: 6 }                       // Right

const E = Value.Diff(L, R)                           // const E = [
                                                     //   { type: 'update', path: '/y', value: 4 },
                                                     //   { type: 'update', path: '/z', value: 5 },
                                                     //   { type: 'insert', path: '/w', value: 6 },
                                                     //   { type: 'delete', path: '/x' }
                                                     // ]

// Patch Left with Edits

const A = Value.Patch(L, E)                          // const A = { y: 4, z: 5, w: 6 }
```

(also shown with indentation in docs)

```typescript
const L = { x: 1, y: 2, z: 3 }                       // Left
    const R = { y: 4, z: 5, w: 6 }                       // Right
    
    const E = Value.Diff(L, R)                           // const E = [
                                                         //   { type: 'update', path: '/y', value: 4 },
                                                         //   { type: 'update', path: '/z', value: 5 },
                                                         //   { type: 'insert', path: '/w', value: 6 },
                                                         //   { type: 'delete', path: '/x' }
                                                         // ]
    
    // Patch Left with Edits
    
    const A = Value.Patch(L, E)                          // const A = { y: 4, z: 5, w: 6 }
```

## Value.Hash (structural hash)

TypeScript:

```typescript
const A = Value.Hash({ x: 1, y: 2, z: 3 })           // const A = '0834a0916e3e4db0'

const B = Value.Hash({ x: 1, y: 4, z: 3 })           // const B = '279c16b78fba6600'
```

JavaScript:

```javascript
const A = Value.Hash({ x: 1, y: 2, z: 3 });
// Expected output: '0834a0916e3e4db0'

const B = Value.Hash({ x: 1, y: 4, z: 3 });
// Expected output: '279c16b78fba6600'
```

## Value.Clone and Value.Equal

```typescript
import Value from 'typebox/value'

// Deep clone supporting Map, Set, TypedArrays
const original = { x: 1, y: { z: 2 }, date: new Date() }
const cloned = Value.Clone(original)

// cloned.y.z = 3  // Does not affect original

// Deep equality check
const equal = Value.Equal(
  { x: 1, y: [2, 3] },
  { x: 1, y: [2, 3] }
)  // true

const notEqual = Value.Equal(
  { x: 1, y: [2, 3] },
  { x: 1, y: [3, 2] }
)  // false

```

## Value.Mutate (preserve object/array references)

TypeScript:

```typescript
const Y = { z: 1 }

const X = { y: Y }

const Z = { x: X }

// Mutation

Value.Mutate(Z, { x: { y: { z: 2 } } })

const A = Z.x.y.z === 2

const B = Z.x.y === Y

const C = Z.x === X
```

JavaScript:

```javascript
const Y = { z: 1 }                                  // const Y = { z: 1 }
    
    const X = { y: Y }                                  // const X = { y: { z: 1 } }
    
    const Z = { x: X }                                  // const Z = { x: { y: { z: 1 } } }
    
    // Mutation
    
    Value.Mutate(Z, { x: { y: { z: 2 } } })             // Z = { x: { y: { z: 2 } } }
    
    const A = Z.x.y.z === 2                             // const A = true
    
    const B = Z.x.y === Y                               // const B = true
    
    const C = Z.x === X                                 // const C = true
```

## Encode/Decode transformations (Type.Codec)

```typescript
import Type from 'typebox'
import Value from 'typebox/value'

// Simple codec for case conversion
const UppercaseString = Type.Codec(Type.String())
  .Decode((value) => value.toUpperCase())
  .Encode((value) => value.toLowerCase())

Value.Decode(UppercaseString, 'hello')  // 'HELLO'
Value.Encode(UppercaseString, 'HELLO')  // 'hello'

// Date codec for ISO string conversion
const DateType = Type.Codec(Type.String({ format: 'date-time' }))
  .Decode((value) => new Date(value))
  .Encode((value) => value.toISOString())

const decoded = Value.Decode(DateType, '2023-01-01T00:00:00Z')
// Result: Date object

const encoded = Value.Encode(DateType, new Date())
// Result: ISO string

// Numeric ID codec
const NumericId = Type.Codec(Type.String())
  .Decode((value) => parseInt(value, 10))
  .Encode((value) => value.toString())
```