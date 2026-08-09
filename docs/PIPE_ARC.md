# Pipe Arc

## Goal

Introduce a primitive for curved pipes.

`pipeArc` generates a solid pipe following a circular arc. HTML and GLB renderers
use a shared capped mesh, while the Roblox renderer keeps a lightweight fallback
made from short cylinders.

No new rendering logic is required in Roblox or HTML beyond ordinary cylinders.

---

## Syntax

```sgsl
pipeArc FillPipe
    at 0 0 0

    pipeRadius 0.08
    bendRadius 0.50

    angle 90
    segments 8

    rotate 0 0 0

    color lightgray
```

---

## Properties

| Property | Meaning |
|----------|---------|
| `at` | Local origin of the arc |
| `pipeRadius` | Radius of the pipe |
| `bendRadius` | Radius of the bend (pipe centerline) |
| `angle` | Arc angle in degrees (positive or negative) |
| `segments` | Number of cylinders used to approximate the arc |
| `rotate` | Orientation of the whole arc |
| `color` | Pipe color |
| `transparency` | Optional transparency from `0` to `1` |

---

## Semantics

Default orientation:

- arc lies in the XY plane
- `at` is the start of the pipe centerline
- starts tangent to +X
- bends toward +Y
- a negative angle bends toward -Y while still starting tangent to +X

`rotate` changes the final orientation in world space.

---

## Mesh generation

The HTML and GLB backends use the same swept-tube mesh generator. It creates:

- a circular cross-section at each path segment,
- the outer tube surface,
- a closed cap at both ends.

The `segments` parameter controls both the path resolution and circular
cross-section resolution for the exported mesh.

## Roblox fallback

Roblox output expands `pipeArc` into `segments` short cylinders. This keeps the
generated Lua compatible with the existing Part-based runtime without requiring
an uploaded mesh asset. The fallback can look slightly faceted; the imported
GLB is the smooth representation for Roblox scenes that use mesh assets.

Each cylinder:

- has length = arcLength / segments
- is placed at the angular midpoint of its section on the arc centerline
- has its Y axis rotated tangent to the arc

where

```
arcLength = bendRadius × radians(angle)
```

The segment length uses the absolute value of `arcLength`. Increasing
`segments` makes the bend smoother without changing its intended centerline
length.

For a positive arc, a segment midpoint at angle `t` has this local position:

```text
x = bendRadius * sin(t)
y = bendRadius * (1 - cos(t))
z = 0
```

The complete `pipeArc` rotation is then applied to both segment positions and
orientations. Expansion happens before rendering, so HTML preview and Roblox
consume the same cylinders.

---

## Example

90° elbow:

```sgsl
pipeArc Outlet
    at 0 0 0
    pipeRadius 0.08
    bendRadius 0.50
    angle 90
    segments 8
```

45° bend:

```sgsl
pipeArc Outlet
    at 0 0 0
    pipeRadius 0.08
    bendRadius 0.50
    angle 45
    segments 4
```

---

## Backward compatibility

Fully backward compatible.

Adds one new primitive only.

## Validation

- `pipeRadius` must be positive.
- `bendRadius` must be positive.
- `angle` must be non-zero and may be positive or negative.
- `segments` must be a positive integer.
