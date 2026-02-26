# Compile Module — High-Performance Validators

The `Compile` module compiles schemas into optimized validators with JIT code generation.

## Compile a schema

```typescript
import { Compile } from 'typebox/compile'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

const validator = Compile(T)

// All Value operations available on compiled validators
validator.Check({ x: 1, y: 2 })           // true
validator.Parse({ x: '1', y: '2' })       // { x: 1, y: 2 }
validator.Create()                         // { x: 0, y: 0 }
validator.Clean({ x: 1, y: 2, z: 3 })     // { x: 1, y: 2 }
validator.Errors({ x: 'invalid' })        // Array of validation errors

// Inspect compiled validator
const code = validator.Code()              // Generated validation code
const isOptimized = validator.IsEvaluated()  // true if using eval
```

## Compile with references (context + Type.Ref)

```typescript
import { Compile } from 'typebox/compile'
import Type from 'typebox'

// Define reusable types in context
const context = {
  User: Type.Object({
    id: Type.String({ format: 'uuid' }),
    name: Type.String()
  }),
  Post: Type.Object({
    id: Type.String({ format: 'uuid' }),
    userId: Type.String({ format: 'uuid' }),
    title: Type.String(),
    content: Type.String()
  })
}

// Reference types from context
const UserValidator = Compile(context, Type.Ref('User'))
const PostValidator = Compile(context, Type.Ref('Post'))

UserValidator.Check({ id: '550e8400-e29b-41d4-a716-446655440000', name: 'John' })  // true
```

## Compile nested validators

```typescript
import { Compile } from 'typebox/compile'
import Type from 'typebox'

// Compile nested validators separately
const NumberValidator = Compile(Type.Number())
const ArrayValidator = Compile(Type.Array(NumberValidator))
const ObjectValidator = Compile(Type.Object({
  data: ArrayValidator,
  count: NumberValidator
}))

const value = { data: [1, 2, 3], count: 3 }
ObjectValidator.Check(value)   // true
ObjectValidator.Parse(value)   // Returns validated and transformed value
```