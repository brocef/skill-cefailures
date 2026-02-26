# Value Module — Runtime Validation and Transformation

The `Value` module provides runtime operations for validation and transformation.

## Value.Check (boolean validation)

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

// Check returns boolean
const valid = Value.Check(T, { x: 1, y: 2 })  // true
const invalid = Value.Check(T, { x: 'not a number', y: 2 })  // false

// Check with error details
if (!Value.Check(T, data)) {
  const errors = Value.Errors(T, data)
  for (const error of errors) {
    console.log(error.path, error.message)
  }
}
```

## Value.Parse (validation with transformation)

Parse applies: `Clone -> Default -> Convert -> Clean -> Assert`.

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number({ default: 10 }),
  z: Type.Optional(Type.Number())
})

// Parse applies: Clone -> Default -> Convert -> Clean -> Assert
try {
  const result = Value.Parse(T, { x: '5', extra: 'field' })
  // Result: { x: 5, y: 10 }
  // - Converts string '5' to number 5
  // - Applies default value 10 to y
  // - Removes 'extra' field (cleaning)
} catch (error) {
  // ParseError thrown if validation fails
  console.error(error.message)
}
```

## Value.Create (generate default values)

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

// Schema with defaults
const T = Type.Object({
  x: Type.Number({ default: 1 }),
  y: Type.Number({ default: 2 }),
  z: Type.Number({ default: 3 })
})

const value = Value.Create(T)
// Result: { x: 1, y: 2, z: 3 }

// Without defaults, generates zero values
const T2 = Type.Object({
  x: Type.Number(),
  y: Type.String(),
  z: Type.Boolean()
})

const value2 = Value.Create(T2)
// Result: { x: 0, y: '', z: false }
```

## Value.Clone and Value.Equal

```typescript
import Value from 'typebox/value'

// Deep clone supporting Map, Set, TypedArrays
const original = { x: 1, y: { z: 2 }, date: new Date() }
const cloned = Value.Clone(original)

cloned.y.z = 3  // Does not affect original

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

## Value.Convert, Value.Clean, Value.Default

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

// Convert - coerce values to target type
const T1 = Type.Number()
const converted = Value.Convert(T1, '100')  // 100 (string to number)

// Clean - remove additional properties
const T2 = Type.Object({ x: Type.Number() })
const cleaned = Value.Clean(T2, { x: 1, y: 2, z: 3 })  // { x: 1 }

// Default - apply default values
const T3 = Type.String({ default: 'hello' })
const defaulted = Value.Default(T3, undefined)  // 'hello'
```

## Value.Assert and Value.Errors

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T = Type.Object({
  email: Type.String({ format: 'email' }),
  age: Type.Integer({ minimum: 0, maximum: 150 })
})

// Assert - throws on validation failure
try {
  Value.Assert(T, { email: 'user@domain.com', age: 25 })  // OK
  Value.Assert(T, { email: 'invalid', age: -5 })  // Throws AssertError
} catch (error) {
  console.error('Assertion failed:', error.message)
}

// Errors - get detailed validation errors
const data = { email: 'not-an-email', age: 200 }
const errors = Value.Errors(T, data)

for (const error of errors) {
  console.log(`Path: ${error.instancePath}`)
  console.log(`Message: ${error.message}`)
  console.log(`Schema path: ${error.schemaPath}`)
}
```