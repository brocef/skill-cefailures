# TypeScript Style

## Naming Conventions

### `SCREAMING_SNAKE_CASE` — Proper Constants Only

Use for hard-coded values and enum members. Do NOT use for every `const` declaration.

```typescript
// Correct: hard-coded values
const MAX_RETRIES = 3
const DEFAULT_TIMEOUT_MS = 5000
const API_BASE_URL = 'https://api.example.com'

// Correct: enum members (enum name is PascalCase, members are SCREAMING_SNAKE_CASE)
enum TaskStatus {
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

### `kebab-case` — File Names

All TypeScript/JavaScript file names use `kebab-case`.

```
// Correct
user-profile.ts
api-client.tsx
get-user-by-id.test.ts

// Wrong
userProfile.ts
ApiClient.tsx
GetUserById.test.ts
```

### `T`-Prefixed `PascalCase` — Type Aliases and Interfaces

All type aliases and interfaces use `T`-prefixed `PascalCase`.

```typescript
// Correct
type TCoreArgument = { name: string; value: unknown }
type TFormulaAST = { op: string; children: TFormulaAST[] }
type TUUID = string
interface TUserProfile { name: string; age: number }

// Wrong: missing T prefix
type CoreArgument = { name: string; value: unknown }
interface UserProfile { name: string; age: number }
```

### `camelCase` — Default

All variables, functions, methods, and properties use `camelCase` unless another rule applies.

### `PascalCase` — Enums, Type Parameters, Schema Objects, Class-Like Constructors, and React Components

Allowed for enum names (members stay `SCREAMING_SNAKE_CASE` — see above), type parameters, `const` variables that are TypeBox schema objects, similar class-like/constructor-like values, or React functional components.

```typescript
// Correct: type parameters
function merge<TSource, TTarget>(source: TSource, target: TTarget): TSource & TTarget
type Result<TValue, TError = Error> = { ok: true; value: TValue } | { ok: false; error: TError }

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
| `kebab-case` | File names |
| `SCREAMING_SNAKE_CASE` | Hard-coded values, enum members |
| `TPascalCase` | Type aliases, interfaces |
| `PascalCase` | Classes, enums, type parameters, schema objects, class-like constructors, React components |
| `camelCase` | Variables, functions, methods, properties |
| Exempt | Destructured variables, imports, override methods |

## Fixing Type Lint Errors

When fixing lint errors or warnings related to types, **never use type casts to silence them** unless there is genuinely no alternative. Casting to `any`, `unknown`, or using `as` to force a type is forbidden as a first resort.

### Required approach

1. **Trace both sides.** Identify the expected type and the provided type. Read the type definitions — don't guess.
2. **Understand why inference fails.** The mismatch is a signal. Common root causes:
   - A function returns a broader type than intended (fix the return type or narrow with a type guard).
   - A variable was initialized with the wrong shape (fix the initialization).
   - A generic parameter wasn't constrained or inferred correctly (add or fix the constraint).
   - An API contract changed upstream (update the consuming code to match).
3. **Fix the actual issue.** If the mismatch reveals a logical bug — wrong field name, missing null check, incorrect function call — fix the logic, not the types.
4. **Narrow, don't cast.** When runtime narrowing is needed, use type guards, discriminated unions, or conditional checks — not `as`.

### What's forbidden

```typescript
// Forbidden: casting to silence the error
const user = getResponse() as TUser
const data = result as any
const id = value as unknown as string

// Acceptable only as last resort with explanation:
// e.g., third-party library with incorrect/missing type definitions
// where a PR or @ts-expect-error with a tracking issue is not viable
```

### When casting is acceptable

A cast is acceptable **only** when all of the following are true:

- You have traced both sides and understand the mismatch.
- The mismatch is caused by something outside your control (e.g., incorrect third-party types).
- There is no type guard, generic constraint, or code fix that resolves it.
- You add a comment explaining why the cast is necessary.

### Database migrations

In DB migrations, the ORM/adapter types reflect the **current** table schema, but the migration operates on a **previous** structure. Type mismatches here are expected and unavoidable — casts or `@ts-expect-error` are acceptable without further investigation.

## LSP Usage

When navigating unfamiliar TypeScript code, prefer the LSP tool over grep for:
- **Hover** — get the resolved type of a symbol without reading its definition file
- **Go-to-definition** — jump to the actual declaration, even across packages
- **Find references** — discover all call sites and usages

Use grep for text-based searches (string literals, comments, patterns). Use LSP when you need type-aware navigation.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `SCREAMING_SNAKE_CASE` for every `const` | Only use for true constants (hard-coded values). A `const` binding to a function call result is `camelCase`. |
| Using `camelCase` for a TypeBox schema `const` | `PascalCase` is correct for schema objects and class-like constructors. |
