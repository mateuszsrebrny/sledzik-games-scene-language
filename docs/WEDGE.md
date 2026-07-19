# Wedge

`wedge` describes a right triangular prism. It is useful for gables, ramps,
sloped roof fills, and similar low-poly geometry.

```sgsl
wedge RoofHalf
    at 0 2 0
    size 4 2 0.4
    rotate 0 90 0
    color red
```

The dimensions use the same `X Y Z` convention as `block`. The triangular
cross-section lies in the local YZ plane and the shape is extruded along local
X. Its slope rises from local `-Z` to local `+Z`.

The Roblox renderer maps this primitive to a native `WedgePart`. HTML preview
and GLB output generate matching triangular-prism geometry.
