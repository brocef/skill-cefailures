## Record types (dictionaries / maps)

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

## Custom format registration (hex-color)

```typescript
import Format from 'typebox/format'

// ------------------------------------------------------------------
// Set
// ------------------------------------------------------------------
Format.Set('hex-color', value => {
  
  return /^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$/.test(value)
})

// ------------------------------------------------------------------
// Get
// ------------------------------------------------------------------
const IsHexColor = Format.Get('hex-color')

// ------------------------------------------------------------------
// Use
// ------------------------------------------------------------------
IsHexColor('#FF5733')                               // true
IsHexColor('#FFF')                                  // true
IsHexColor('blue')                                  // false
```

```typescript
import { Type, Value } from 'typebox'

const T = Type.String({ format: 'hex-color' })      // const T = { type: 'string', format: 'hex-color' }

const R = Value.Check(T, '#FFFFFF')                 // true

const R = Value.Check(T, 'blue')                    // false
```

## Custom format registration (credit-card)

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

## Configure TypeBox settings (enumerable compositor kind)

```typescript
import { Settings } from 'typebox/system'

Settings.Set({ enumerableKind: true })

console.log(Type.String())
```