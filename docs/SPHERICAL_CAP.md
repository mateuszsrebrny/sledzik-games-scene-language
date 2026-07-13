# ŚGSL Extension Proposal: Spherical Cap

## Goal

Add a rounded end-cap primitive for bodies that should not end in a flat face.

`sphericalCap` is intended for shapes such as:

- tanks,
- bottle shoulders,
- rounded roofs,
- domed covers,
- pressure vessel ends.

The primitive belongs to the same geometry layer as blocks, cylinders, and frustums.
It does not depend on any renderer-specific feature.

---

## Syntax

```sgsl
sphericalCap TankTop
    at 0 8 0

    baseRadius 1.6
    height 0.65
    segments 6

    rotate 0 0 0
    color darkgray
```

---

## Properties

| Property | Meaning |
|----------|---------|
| `at` | Center position of the cap |
| `baseRadius` | Radius where the cap joins the body |
| `height` | Total height of the cap |
| `segments` | Number of stacked frustums used for approximation |
| `rotate` | Orientation of the cap |
| `color` | Render color |

---

## Semantics

- The cap is centered on its own bounding box.
- It extends along the local positive Y axis.
- The visible surface follows a spherical profile.
- Internally it is expanded into `segments` short frustums.
- Segment radii are sampled from the sphere curve, not linearly interpolated.
- `rotate` orients the full cap before renderer export.

Bottom caps can be created by rotating the primitive 180 degrees.

---

## Example

```sgsl
cylinder TankBody
    radius 1.6
    height 6

sphericalCap TankTop
    at 0 6.325 0
    baseRadius 1.6
    height 0.65
    segments 6

sphericalCap TankBottom
    at 0 -0.325 0
    baseRadius 1.6
    height 0.65
    segments 6
    rotate 180 0 0
```

---

## Backward Compatibility

This is a new primitive only.

Existing `.sgsl` files remain valid and do not change behavior.

---

## Open Questions

- Should `segments` have a default value?
- Should the primitive support a separate `topRadius` override for asymmetric caps?
- Should the cap allow inversion without requiring a 180-degree rotation?
