## Install

```bash
npm install typebox
```

## Build object schemas (with inference)

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

## Add constraints and metadata

```typescript
const T = Type.Number({
  minimum: 0,
  maximum: 100
})

const S = Type.String({
  format: 'email'
})

const M = Type.Object({
  id: Type.String(),
  message: Type.String()
}, {
  description: 'A protocol message'
})
```

(Also shown in the design docs)

```typescript
const T = Type.Number({
  minimum: 0,
  maximum: 100
})

const S = Type.String({
  format: 'email'
})
```