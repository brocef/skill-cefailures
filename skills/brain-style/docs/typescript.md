# TypeScript Style

## Naming Conventions

### `SCREAMING_SNAKE_CASE` — Proper Constants Only

Use for hard-coded values and enum members. Do NOT use for every `const` declaration.

```typescript
// Correct: hard-coded values
const MAX_RETRIES = 3
const DEFAULT_TIMEOUT_MS = 5000
const API_BASE_URL = 'https://api.example.com'

// Correct: enum members
enum Status {
  NOT_STARTED = 'NOT_STARTED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
}

// Wrong: not a proper constant, just a const binding
const MY_LOGGER = createLogger('app')
// Correct:
const myLogger = createLogger('app')

// Wrong: computed or derived values are not proper constants
const FILTERED_ITEMS = items.filter(i => i.active)
// Correct:
const filteredItems = items.filter(i => i.active)
```

### `PascalCase` — Schema Objects, Class-Like Constructors, and React Components

Allowed for `const` variables that are TypeBox schema objects, similar class-like/constructor-like values, or React functional components.

```typescript
// Correct: TypeBox schema objects
const UserSchema = Type.Object({
  name: Type.String(),
  age: Type.Number(),
})

// Correct: React functional components
const UserProfile = ({ name }: UserProfileProps) => {
  return <div>{name}</div>
}

// Correct: other class-like constructor patterns
const MyComponent = styled.div`...`
const UserModel = defineModel({...})
```

### Naming Exemptions

The following are **exempt** from naming enforcement — do not rename or flag these:

| Category | Reason | Example |
|----------|--------|---------|
| Destructured variables | Source object determines naming | `const { user_name } = apiResponse` |
| Imports | External package controls export names | `import { Some_Thing } from 'library'` |
| Override methods | Parent class determines the name | `override get_value() { ... }` |

When you encounter a naming style that looks wrong, check whether it falls into an exempt category before flagging or renaming.

## Quick Reference

| Style | Use For |
|-------|---------|
| `SCREAMING_SNAKE_CASE` | Hard-coded values, enum members |
| `PascalCase` | Types, interfaces, classes, schema objects, class-like constructors, React components |
| `camelCase` | Variables, functions, methods, properties |
| Exempt | Destructured variables, imports, override methods |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `SCREAMING_SNAKE_CASE` for every `const` | Only use for true constants (hard-coded values). A `const` binding to a function call result is `camelCase`. |
| Renaming a destructured variable to match conventions | Leave it — the source determines the name. If you need a different name, use aliasing: `const { user_name: userName } = obj` |
| Flagging an import's naming style | Imports are exempt. The external package chose the name. |
| Flagging an override method's naming style | Override methods are exempt. The parent class chose the name. |
| Using `camelCase` for a TypeBox schema `const` | `PascalCase` is correct for schema objects and class-like constructors. |
