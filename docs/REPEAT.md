# Repeated instances

`repeat` creates a sequence of instances of one component.

```sgsl
component DashedRoad
    param dashCount 4
    param dashSpacing 4.1

    repeat Dash RoadDash
        count dashCount
        at -6.2 0.06 0
        step dashSpacing 0 0
```

The syntax is:

```text
repeat <name-prefix> <component-name>
    count <non-negative integer expression>
    at <x> <y> <z>
    step <x> <y> <z>
```

`at` defaults to `(0, 0, 0)` and `step` defaults to `(0, 0, 0)`.
Generated instances use a numeric suffix, for example `Dash01`, `Dash02`,
and `Dash03`.

A repeat accepts the same optional properties as an `instance`, including
`rotate`, `scale`, `mirror`, `emissive`, and parameter overrides with `set`.
The repeat offset is local to its containing component, so rotating or scaling
the parent also transforms the complete repeated sequence.

The maximum supported count is `10000`.
