# Formats, Refine, and Codec

## Format validation

```typescript
import { Format } from 'typebox/format'
import Type from 'typebox'

// Built-in format checks
const validEmail = Format.Test('email', 'user@domain.com')  // true
const invalidEmail = Format.Test('email', 'not-an-email')  // false

// Available formats: email, uuid, date-time, date, time,
// ipv4, ipv6, uri, hostname, regex, duration, url, etc.

// Use in type definitions
const UserSchema = Type.Object({
  email: Type.String({ format: 'email' }),
  website: Type.String({ format: 'url' }),
  created: Type.String({ format: 'date-time' }),
  id: Type.String({ format: 'uuid' })
})
```

## Custom format registration

```typescript
import { Format } from 'typebox/format'
import Type from 'typebox'

// Register custom format
Format.Set('credit-card', (value: string) => {
  // Luhn algorithm validation
  const digits = value.replace(/\D/g, '')
  if (digits.length !== 16) return false

  let sum = 0
  for (let i = 0; i < digits.length; i++) {
    let digit = parseInt(digits[i])
    if (i % 2 === 0) {
      digit *= 2
      if (digit > 9) digit -= 9
    }
    sum += digit
  }
  return sum % 10 === 0
})

// Use custom format
const PaymentSchema = Type.Object({
  cardNumber: Type.String({ format: 'credit-card' }),
  cvv: Type.String({ pattern: '^[0-9]{3,4}$' })
})

// Check if format exists
Format.Has('credit-card')  // true

// Get format validator
const validator = Format.Get('credit-card')
validator('4532015112830366')  // true
```

## Refine — custom validation logic

```typescript
import Type from 'typebox'
import Value from 'typebox/value'

// Refine with custom predicate
const EvenNumber = Type.Refine(
  Type.Number(),
  (value) => value % 2 === 0,
  {
    errorMessage: 'Expected even number'
  }
)

Value.Check(EvenNumber, 4)  // true
Value.Check(EvenNumber, 3)  // false

// Multiple refinements
const PositiveEvenNumber = Type.Refine(
  EvenNumber,
  (value) => value > 0,
  {
    errorMessage: 'Expected positive number'
  }
)

// Complex refinement with context
const StrongPassword = Type.Refine(
  Type.String({ minLength: 8 }),
  (value) => {
    return /[A-Z]/.test(value) &&
           /[a-z]/.test(value) &&
           /[0-9]/.test(value) &&
           /[^A-Za-z0-9]/.test(value)
  },
  {
    errorMessage: 'Password must contain uppercase, lowercase, number, and special character'
  }
)
```

## Codec — encode and decode transformations

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