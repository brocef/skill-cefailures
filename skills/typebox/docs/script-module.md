# Script — TypeScript Syntax to Schema

The `Script` functionality converts TypeScript syntax strings into JSON Schema.

## Basic usage

```typescript
import Type from 'typebox'

// Basic object type
const T = Type.Script(`{
  x: number,
  y: number,
  z: number
}`)

type T = Type.Static<typeof T>  // { x: number, y: number, z: number }

// Union types
const Status = Type.Script(`'active' | 'pending' | 'inactive'`)

// Complex types with arrays and nested objects
const User = Type.Script(`{
  id: string,
  name: string,
  emails: string[],
  profile: {
    age: number,
    country: string
  }
}`)
```

## Script with context and mapped types

```typescript
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

// Map over keys to transform types
const S = Type.Script({ T }, `{
  [K in keyof T]: T[K] | null
}`)

type S = Type.Static<typeof S>
// { x: number | null, y: number | null, z: number | null }

// Partial using mapped types
const P = Type.Script({ T }, `{
  [K in keyof T]?: T[K]
}`)

type P = Type.Static<typeof P>
// { x?: number, y?: number, z?: number }
```

## Script type actions (utility types)

```typescript
import Type from 'typebox'

const User = Type.Object({
  id: Type.String(),
  name: Type.String(),
  email: Type.String(),
  password: Type.String()
})

// Pick specific properties
const PublicUser = Type.Script({ User }, `Pick<User, 'id' | 'name' | 'email'>`)

// Make properties optional
const UpdateUser = Type.Script({ User }, `Partial<User>`)

// Omit sensitive fields
const SafeUser = Type.Script({ User }, `Omit<User, 'password'>`)

// Extract keys
const UserKey = Type.Script({ User }, `keyof User`)
type UserKey = Type.Static<typeof UserKey>  // 'id' | 'name' | 'email' | 'password'

// Record types
const Scores = Type.Script(`Record<string, number>`)
```

## Script modules

```typescript
import Type from 'typebox'
import { Compile } from 'typebox/compile'

const { User, Post, Comment } = Type.Script(`
  type User = {
    id: string,
    name: string,
    email: string
  }

  type Post = {
    id: string,
    userId: string,
    title: string,
    content: string
  }

  type Comment = {
    id: string,
    postId: string,
    userId: string,
    text: string
  }
`)

// Use types individually
const UserValidator = Compile({ User, Post, Comment }, Type.Ref('User'))
const PostValidator = Compile({ User, Post, Comment }, Type.Ref('Post'))
```