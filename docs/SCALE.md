# Instance Scale

Every component instance may define a uniform scale:

```sgsl
instance SmallBottle Bottle
    at 4 0 0
    scale 0.5
```

The default scale is `1`. Scale must be greater than zero and may be an
expression using parameters visible to the instance.

## Semantics

Instance transforms use this order:

```text
worldTransform = parentTransform * translation * rotation * scale
```

Uniform scale affects the complete local coordinate system of the component:

- primitive dimensions, radii, and heights,
- primitive positions relative to the component origin,
- nested instance positions,
- all descendants of nested instances.

The instance's own `at` position is not scaled by its own scale. It is expressed
in the coordinate system of its parent.

## Nested scale

Scales multiply through the component tree:

```sgsl
component Crate
    instance SmallBottle Bottle
        at 2 0 0
        scale 0.5

instance SmallCrate Crate
    at 10 0 0
    scale 0.5
```

`SmallBottle` has an effective world scale of `0.25`. Its local position inside
`Crate` is also scaled by `SmallCrate`.

Only uniform scaling is supported. Separate X, Y, and Z scale values are not
part of the language.
