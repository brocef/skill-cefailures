## Make object properties required (Type.Required)

```typescript
import { Type } from '@sinclair/typebox';

const T = Type.Object({
  x: Type.Optional(Type.Number()),
  y: Type.Optional(Type.Number()),
  z: Type.Optional(Type.Number())
});

const S = Type.Required(T);
```

(also shown without import)

```typescript
const T = Type.Object({
  x: Type.Optional(Type.Number()),
  y: Type.Optional(Type.Number()),
  z: Type.Optional(Type.Number())
})

const S = Type.Required(T)
```

## Make object properties optional (Type.Partial)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

const S = Type.Partial(T)
```

## Extract keys from an object schema (Type.KeyOf)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

const S = Type.KeyOf(T)                             // const S: TUnion<[
                                                    //  TLiteral<'x'>,
                                                    //  TLiteral<'y'>,
                                                    //  TLiteral<'z'>
                                                    // ]>
```

## Pick a subset of properties (Type.Pick)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

const S = Type.Pick(T, Type.Union([
  Type.Literal('x'),
  Type.Literal('y')
]))
```

## Mapped transformations (Type.Mapped)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

                                                    // type S = { 
                                                    //   [K in keyof T]: T[K] | null 
                                                    // }

const S = Type.Mapped(
  Type.Identifier('K'),
  Type.KeyOf(T),
  Type.Ref('K'),
  Type.Union([
    Type.Index(T, Type.Ref('K')),
    Type.Null()
  ])
)
```

## Intersections (Type.Intersect) and options

```typescript
const T = Type.Intersect([
  Type.Object({ x: Type.Number() }),
  Type.Object({ y: Type.Number() }),
])

type T = Static<typeof T>
```

Intersect options interface:

```typescript
export interface TIntersectOptions extends TSchemaOptions {
  /** 
   * A schema to apply to any properties in the object that were not validated 
   * by other keywords like `properties`, `patternProperties`, or `additionalProperties`. 
   * If `false`, no additional properties are allowed. 
   */
  unevaluatedProperties?: TSchema | boolean
}
```

## Cross-property validation (Type.Refine)

```typescript
import { Type, Value } from '@sinclair/typebox'

const T = Type.Refine(Type.Object({
  x: Type.Number(),
  y: Type.Number()
}), value => {
  return value.x === value.y
}, 'x and y should be equal')

const E = Value.Errors(T, { x: 1, y: 2 })
```

(also shown without imports)

```typescript
const T = Type.Refine(Type.Object({
  x: Type.Number(),
  y: Type.Number()
}), value => {
  return value.x === value.y
}, 'x and y should be equal')

const E = Value.Errors(T, { x: 1, y: 2 })
```