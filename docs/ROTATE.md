# ŚGSL Extension Proposal: Rotation

## Goal

Allow every scene object to define its orientation.

The object geometry remains unchanged.

Rotation changes only the transform applied by renderers.

---

# Philosophy

Every scene object has three basic transforms:

- Position (`at`)
- Rotation (`rotate`)
- Size (`size`) or Radius/Height

Rotation should work identically for every object type.

Supported objects:

- block
- cylinder
- frustum

Future objects automatically inherit rotation support.

---

# Syntax

Rotation is optional.

Example:

```sgsl
block Beam
    at 0 5 0
    size 8 0.3 0.3

    rotate 0 0 35

    color gray
```

---

# Grammar

Add optional property:

```lark
property:

      at
    | size
    | color
    | anchor
    | rotate
    | override
```

Rule:

```lark
rotate:

    "rotate" NUMBER NUMBER NUMBER
```

---

# Meaning

Rotation is expressed as Euler angles.

Units:

degrees.

Order:

```text
rotate X Y Z
```

The rotations use the same intrinsic XYZ convention as Three.js Euler XYZ
and Roblox `CFrame.Angles`: the resulting transform is `Rx * Ry * Rz`.

Examples:

```sgsl
rotate 0 90 0
```

Rotate 90° around Y axis.

```sgsl
rotate 15 0 0
```

Tilt 15° around X axis.

```sgsl
rotate 30 45 10
```

Rotate around all three axes.

---

# Default value

If omitted:

```text
rotate 0 0 0
```

Therefore all existing SGSL files remain valid.

---

# Internal Scene Model

Current object:

```json
{
    "type":"block",

    "at":[0,0,0],

    "size":[4,2,1]
}
```

becomes

```json
{
    "type":"block",

    "at":[0,0,0],

    "rotation":[0,45,0],

    "size":[4,2,1]
}
```

Rotation is always stored in degrees.

---

# HTML Renderer

Convert degrees to radians.

Apply:

```text
rotation.x

rotation.y

rotation.z
```

using the standard Three.js Euler rotation.

---

# Roblox Renderer

Apply rotation using CFrame.

Suggested implementation:

```lua
CFrame.new(position)
    * CFrame.Angles(
        math.rad(rx),
        math.rad(ry),
        math.rad(rz)
    )
```

The renderer is responsible for any object-specific corrections.

Example:

Roblox cylinders require a built-in correction because their local axis differs from SGSL.

This correction should remain inside the Builder runtime.

SGSL should never know about Roblox-specific conventions.

---

# Interaction with Anchor

Anchor is resolved first.

Process:

1.

Read:

at

size

anchor

2.

Compute object center.

3.

Create transform.

4.

Apply rotation around the computed center.

Rotation never changes the anchor position.

---

# Examples

## Rotated beam

```sgsl
block Beam

    at 0 4 0

    size 8 0.3 0.3

    rotate 0 0 25

    color gray
```

---

## Horizontal pipe

```sgsl
cylinder Pipe

    at 0 3 0

    radius 0.15

    height 5

    rotate 0 0 90

    color lightgray
```

---

## Inclined pipe

```sgsl
cylinder Pipe

    at 0 3 0

    radius 0.15

    height 5

    rotate 30 0 90

    color lightgray
```

---

## Sloped roof

```sgsl
block Roof

    at 0 8 0

    size 16 0.3 8

    rotate 15 0 0

    color lightgray
```

---

# Backward Compatibility

Fully backward compatible.

Existing SGSL files behave exactly as before.

Objects without rotation are interpreted as:

```text
rotate 0 0 0
```

---

# Design Philosophy

Rotation belongs to the scene description.

Implementation details remain inside renderers.

SGSL never needs to know how Roblox or Three.js internally represent rotations.

Every backend is responsible for applying the same transform in its own native format.
