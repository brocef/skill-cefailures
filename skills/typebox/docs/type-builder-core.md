# Type Builder (Type) — Core Schema Construction

TypeBox creates in-memory JSON Schema objects that infer as TypeScript types.

## Object types

```typescript
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

// Infer static TypeScript type
type T = Type.Static<typeof T>  // { x: number, y: number, z: number }

// Add constraints and metadata
const UserSchema = Type.Object({
  id: Type.String({ format: 'uuid' }),
  email: Type.String({ format: 'email' }),
  age: Type.Optional(Type.Integer({ minimum: 0, maximum: 150 }))
}, {
  description: 'User object schema',
  additionalProperties: false
})
```

## Array and tuple types

```typescript
import Type from 'typebox'

// Array with uniform element type
const NumberArray = Type.Array(Type.Number(), {
  minItems: 1,
  maxItems: 10
})

// Fixed-length tuple with specific types
const Coordinate = Type.Tuple([
  Type.Number(),
  Type.Number(),
  Type.Number()
])

type Coordinate = Type.Static<typeof Coordinate>  // [number, number, number]
```

## Union and intersection types

```typescript
import Type from 'typebox'

// Union type - value matches any of the types
const Status = Type.Union([
  Type.Literal('active'),
  Type.Literal('pending'),
  Type.Literal('inactive')
])

type Status = Type.Static<typeof Status>  // 'active' | 'pending' | 'inactive'

// Intersection type - value must satisfy all types
const Extended = Type.Intersect([
  Type.Object({ x: Type.Number() }),
  Type.Object({ y: Type.String() })
])

type Extended = Type.Static<typeof Extended>  // { x: number } & { y: string }
```

## Literal and enum types

```typescript
import Type from 'typebox'

// Literal types for specific values
const True = Type.Literal(true)
const FortyTwo = Type.Literal(42)
const Hello = Type.Literal('hello')

// Enum for named constants
const Direction = Type.Enum({
  Up: 'UP',
  Down: 'DOWN',
  Left: 'LEFT',
  Right: 'RIGHT'
})

type Direction = Type.Static<typeof Direction>  // 'UP' | 'DOWN' | 'LEFT' | 'RIGHT'
```

## Record types

```typescript
import Type from 'typebox'

// String keys to number values
const Scores = Type.Record(Type.String(), Type.Number())

type Scores = Type.Static<typeof Scores>  // Record<string, number>

// Pattern-based keys
const ApiEndpoints = Type.Record(
  Type.String({ pattern: '^/api/.*' }),
  Type.Object({
    method: Type.String(),
    handler: Type.String()
  })
)
```

## Recursive and cyclic types

```typescript
import Type from 'typebox'

// Tree structure with recursive children
const Node = Type.Cyclic(Self => Type.Object({
  value: Type.Number(),
  children: Type.Array(Type.Ref(Self))
}))

type Node = Type.Static<typeof Node>
// { value: number, children: Node[] }

// Linked list
const ListNode = Type.Cyclic(Self => Type.Object({
  data: Type.Any(),
  next: Type.Union([Type.Ref(Self), Type.Null()])
}))

// JSON value (recursive union)
const JsonValue = Type.Cyclic(Self => Type.Union([
  Type.String(),
  Type.Number(),
  Type.Boolean(),
  Type.Null(),
  Type.Array(Type.Ref(Self)),
  Type.Record(Type.String(), Type.Ref(Self))
]))
```