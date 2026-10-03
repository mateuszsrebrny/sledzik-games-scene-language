# Mesh orientation (triangle winding)

Every triangle the GLB and HTML renderers emit must be wound
**counter-clockwise as seen from outside the solid** - glTF's front-face
convention. `sgsl/mesh_orientation.py` enforces it, and
`tests/test_mesh_orientation.py` pins it for every generator.

## Why it matters

Roblox draws only a triangle's front face and **ignores glTF's
`doubleSided`**. A solid wound the other way therefore renders inside out:
its near wall is culled, and the inside of the far wall shows through where
the near wall should be. It reads as a solid you can see into: a tree whose
tiers show their inner floors as pale ellipses, a bush with its flowers
visible from inside.

Inward winding also flips the flat normals Roblox derives from it, because
only spheres export explicit normals. Lit surfaces of an inside-out solid
therefore shade dark. That is how it can be misread as a material problem.

## Why nobody saw it

Every exported material sets `doubleSided: true`, so glTF viewers draw both
faces and show nothing wrong. The HTML preview culls back faces like Roblox
does, but mostly draws flat, unlit colours, and the inside of a convex solid
in a flat colour looks exactly like its outside. Only overlapping solids
(stacked tree tiers, intersecting bush caps) gave it away, and then only in
Studio.

## How it is enforced

Generators build their mesh in whatever order is natural and then return
`orient_outward(vertices, indices)`. That function measures the mesh's signed
volume (the sum of `a · (b × c) / 6` over its triangles) and reverses every
triangle when the sign is negative.

Prefer this over fixing a generator's index order. For several generators the
handedness **depends on their parameters**: a `pipeArc` with a negative
`angle` sweeps through a mirrored frame, and a `profileRevolve` listed
top-down revolves the other way. A hard-coded order is right for one call and
wrong for the next. The volume sign is right for all of them.

The volume sign only means something for a **closed, consistently wound**
mesh. A mesh whose parts disagree, such as two end caps closed with the same
order although they face opposite ways, can still total positive.
`test_mesh_orientation.py` therefore checks two things separately:

- the signed volume is positive, and
- after welding coincident vertices, every directed edge occurs once and is
  matched by its reverse (closed and wound one way throughout).

Instance mirroring cannot turn a solid inside out. `mirror` reflects where a
part sits, never the part itself, and its geometry is generated fresh under a
pure rotation.

## Adding a primitive

1. Build a closed mesh with consistent winding.
2. Return `orient_outward(vertices, indices)`.
3. Add it to `GENERATORS` in `tests/test_mesh_orientation.py`, with every
   parameter that can mirror its sweep (negative angles, reversed profiles,
   partial sweeps).
4. Confirm the test fails with `orient_outward` removed before trusting that
   it passes.
