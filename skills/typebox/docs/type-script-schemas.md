## Construct JSON Schema from a TypeScript-like string

```typescript
import Type from 'typebox'

const T = Type.Script(`{
  x: number,
  y: number,
  z: number
}`)                                                 // const T = {
                                                        //   type: 'object',
                                                        //   required: ['x', 'y', 'z'],
                                                        //   properties: {
                                                        //     x: { type: 'number' },
                                                        //     y: { type: 'number' },
                                                        //     z: { type: 'number' }
                                                        //   }
                                                        // }
```

## Map an existing schema using context + mapped types (nullable properties)

```typescript
import Type from 'typebox'

const T = Type.Script(`{ 
  x: number, 
  y: number, 
  z: number 
}`)                                                 // const T = {
                                                    //   type: 'object',
                                                    //   required: ['x', 'y', 'z'],
                                                    //   properties: {
                                                    //     x: { type: 'number' },
                                                    //     y: { type: 'number' },
                                                    //     z: { type: 'number' }
                                                    //   }
                                                    // }

const S = Type.Script({ T }, `{
  [K in keyof T]: T[K] | null
}`)                                                 // const S = {
                                                    //   type: 'object',
                                                    //   required: ['x', 'y', 'z'],
                                                    //   properties: {
                                                    //     x: {
                                                    //       anyOf: [
                                                    //         { type: 'number' }, 
                                                    //         { type: 'null' }
                                                    //       ] 
                                                    //     },
                                                    //     y: {
                                                    //       anyOf: [
                                                    //         { type: 'number' }, 
                                                    //         { type: 'null' }
                                                    //       ] 
                                                    //     },
                                                    //     z: {
                                                    //       anyOf: [
                                                    //         { type: 'number' }, 
                                                    //         { type: 'null' }
                                                    //       ] 
                                                    //     },
                                                    //   }
                                                    // }

type S = Type.Static<typeof S>                      // type S = {
                                                    //   x: number | null,
                                                    //   y: number | null,
                                                    //   z: number | null
                                                    // }
```

(also shown in another overview example)

```typescript
import Type from 'typebox'

const T = Type.Script(`{
  x: number,
  y: number,
  z: number
}`)

const S = Type.Script({ T }, `{
  [K in keyof T]: T[K] | null
}`)
```

## Partial via mapped types in Script

```typescript
import Type from 'typebox'

const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

// Partial using mapped types
const P = Type.Script({ T }, `{ 
  [K in keyof T]?: T[K]
}`)

type P = Type.Static<typeof P>
// { x?: number, y?: number, z?: number }
```

## Map and rename property keys (advanced)

```typescript
const T = Type.Object({
  x: Type.Number(),
  y: Type.Number(),
  z: Type.Number()
})

const S = Type.Script({ T }, '{ [K in keyof T as `prop${Uppercase<K>}`]: T[K] }')

// const S: TObject<{
//   propX: TNumber;
//   propY: TNumber;
//   propZ: TNumber;
// }>
```

## DeepPartial (advanced)

```typescript
const DeepPartial = Type.Script(`<T> = {
  [K in keyof T]?: T[K] extends object
    ? DeepPartial<T[K]>
    : T[K]
}`)

const Result = Type.Script({ DeepPartial }, `DeepPartial<{
  x: {
    y: {
      z: 1
    }
  }
}>`)                                                // const Result: TObject<{
//   x: TOptional<TObject<{
//     y: TOptional<TObject<{
//       z: TOptional<TLiteral<1>>
//     }>>
//   }>>
// }>
```

## Script with options (format example)

```javascript
const Email = Type.Script('string', {
  format: 'email'
})                                  // const Email = {
                                    //   type: 'string',
                                    //   format: 'email'
                                    // }
```

## Embedded types with options (Options<...>)

```javascript
const Vector = Type.Script(`{
  x: Options<number, { minimum: 0 }>,
  y: Options<number, { minimum: 0 }>,
  z: Options<number, { minimum: 0 }>
}`)                                                 // const Vector = {
                                                        //   type: 'object',
                                                        //   required: ['x', 'y', 'z'],
                                                        //   properties: {
                                                        //     x: { type: 'number', minimum: 0 },
                                                        //     y: { type: 'number', minimum: 0 },
                                                        //     z: { type: 'number', minimum: 0 }
                                                        //   }
                                                        // }
```

## Scaling patterns (deep and wide)

### Refactoring deep structures to avoid TypeScript depth limits

```typescript
const D = Type.Script(`{ e: 1 }`)                   // depth + 1
const C = Type.Script({ D }, `{ d: D }`)            // depth + 1
const B = Type.Script({ C }, `{ c: C }`)            // depth + 1
const A = Type.Script({ B }, `{ b: B }`)            // depth + 1

const T = Type.Script({ A }, `{ a: A }`)            // ok
```

### Wide data structure example

```typescript
const T = Type.Script(`[   // 1 x depth
  0, 1, 2, 3, 4, 5, 6, 7,  // 128 x elements  
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7,
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
  0, 1, 2, 3, 4, 5, 6, 7, 
]`)
```

## Const to Script migration example

```typescript
const T = Type.Const({ x: 1, y: 2, z: 3 } as const) // const T: TObject<{
                                                    //   TReadonly<TLiteral<1>>
                                                    //   TReadonly<TLiteral<2>>
                                                    //   TReadonly<TLiteral<3>>
                                                    // }>
```

```typescript
const T = Type.Script(`{ x: 1, y: 2, z: 3 }`)       // const T: TObject<{
                                                    //   x: TLiteral<1>;
                                                    //   y: TLiteral<2>;
                                                    //   z: TLiteral<3>;
                                                    // }>

// Optional: If readonly is required.

const S = Type.Script({ T }, `{
  readonly [K in keyof T]: T[K]
}`)                                                 // const S: TObject<{
                                                    //   x: TReadonly<TLiteral<1>>;
                                                    //   y: TReadonly<TLiteral<2>>;
                                                    //   z: TReadonly<TLiteral<3>>;
                                                    // }>
```