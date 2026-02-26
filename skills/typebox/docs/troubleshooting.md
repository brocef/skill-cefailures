# Troubleshooting and Gotchas

## `Value.Check` is `false` but you need to know why

Use `Value.Errors(schema, data)` to get detailed error information.

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

if (!Value.Check(T, data)) {
  const errors = Value.Errors(T, data)
  for (const error of errors) {
    console.log(error.path, error.message)
  }
}
```

## `Value.Parse` throws

`Value.Parse` throws a `ParseError` if validation fails.

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number({ default: 10 }),
  z: Type.Optional(Type.Number())
})

try {
  const result = Value.Parse(T, { x: '5', extra: 'field' })
} catch (error) {
  console.error(error.message)
}
```

Also note Parse applies a transformation pipeline:

- Clone -> Default -> Convert -> Clean -> Assert

That means input like `{ x: '5' }` can become `{ x: 5 }`, defaults may be applied, and extra fields may be removed.

## Extra properties “disappear” after parsing/cleaning

`Value.Clean` removes additional properties.

```typescript
import Value from 'typebox/value'
import Type from 'typebox'

const T2 = Type.Object({ x: Type.Number() })
const cleaned = Value.Clean(T2, { x: 1, y: 2, z: 3 })  // { x: 1 }
```

## Confusion over error fields (`path` vs `instancePath`)

The docs show both styles in examples:

- `error.path` / `error.message` (used in one snippet)
- `error.instancePath`, `error.schemaPath`, `error.message` (used in another snippet)

When iterating errors, inspect the returned error object shape in your environment and use the appropriate properties.

## Formats not validating as expected

To test formats directly, use `Format.Test(formatName, value)`.

```typescript
import { Format } from 'typebox/format'

const validEmail = Format.Test('email', 'user@domain.com')  // true
const invalidEmail = Format.Test('email', 'not-an-email')  // false
```

If using a custom format, ensure it is registered and available.

```typescript
import { Format } from 'typebox/format'

Format.Has('credit-card')  // true
const validator = Format.Get('credit-card')
validator('4532015112830366')  // true
```

## Compiled validators: how to inspect optimization

`Compile(schema)` returns a validator that can expose the generated code and whether it was evaluated.

```typescript
import { Compile } from 'typebox/compile'
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number()
})

const validator = Compile(T)
const code = validator.Code()              // Generated validation code
const isOptimized = validator.IsEvaluated()  // true if using eval
```