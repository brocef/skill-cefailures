# Type Transformations and Operations

TypeBox includes transformations and type-level operations that work on existing schemas.

## Pick and omit

```typescript
import Type from 'typebox'

const User = Type.Object({
  id: Type.String(),
  email: Type.String(),
  password: Type.String(),
  createdAt: Type.String()
})

// Pick only specific properties
const PublicUser = Type.Pick(User, ['id', 'email'])
type PublicUser = Type.Static<typeof PublicUser>  // { id: string, email: string }

// Omit sensitive properties
const SafeUser = Type.Omit(User, ['password'])
type SafeUser = Type.Static<typeof SafeUser>  // { id: string, email: string, createdAt: string }
```

## Partial and required

```typescript
import Type from 'typebox'

const User = Type.Object({
  id: Type.String(),
  name: Type.String(),
  email: Type.String()
})

// Make all properties optional
const UpdateUser = Type.Partial(User)
type UpdateUser = Type.Static<typeof UpdateUser>  // { id?: string, name?: string, email?: string }

// Make all properties required
const StrictUser = Type.Required(UpdateUser)
type StrictUser = Type.Static<typeof StrictUser>  // { id: string, name: string, email: string }
```

## KeyOf and index

```typescript
import Type from 'typebox'

const Config = Type.Object({
  host: Type.String(),
  port: Type.Number(),
  secure: Type.Boolean()
})

// Extract keys as union of literals
const ConfigKey = Type.KeyOf(Config)
type ConfigKey = Type.Static<typeof ConfigKey>  // 'host' | 'port' | 'secure'

// Index into object to get property type
const PortType = Type.Index(Config, ['port'])
type PortType = Type.Static<typeof PortType>  // number
```

## Exclude and extract from unions

```typescript
import Type from 'typebox'

const Numbers = Type.Union([
  Type.Literal(1),
  Type.Literal(2),
  Type.Literal(3),
  Type.Literal(4)
])

// Exclude specific values
const WithoutOne = Type.Exclude(Numbers, Type.Literal(1))
type WithoutOne = Type.Static<typeof WithoutOne>  // 2 | 3 | 4

// Extract only specific values
const OnlyOne = Type.Extract(Numbers, Type.Literal(1))
type OnlyOne = Type.Static<typeof OnlyOne>  // 1
```