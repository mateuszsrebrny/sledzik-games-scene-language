# Ring

`ring` creates a horizontal circular ring or an angular slice of one. Preview,
GLB, and Roblox output approximate it with tangent block segments.

```sgsl
ring OuterSidewalkCurve
    anchor center bottom center
    at 0 0 0
    radius_inner 4
    radius_outer 6.5
    height 0.22
    start_angle 180
    angle 90
    segments 12
    color #b8bab8
```

## Properties

| Property | Meaning |
| --- | --- |
| `radius_inner` | Inner radius. May be `0` for a filled sector. |
| `radius_outer` | Outer radius; must exceed `radius_inner`. |
| `height` | Vertical thickness. |
| `segments` | Number of blocks across the complete selected angle. |
| `start_angle` | Optional start angle in degrees; defaults to `0`. |
| `angle` | Optional signed sweep in degrees; defaults to `360`. |

Angles lie in the XZ plane. Zero points along `+X`; positive angles sweep
towards `+Z`. `angle` must be non-zero and no larger than one full revolution.

The complete object transform is applied after constructing the local arc, so
`at`, `anchor`, `rotate`, component transforms, and instance transforms work as
they do for other primitives.
