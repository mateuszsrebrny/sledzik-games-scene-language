# Instance mirroring

Instances can be mirrored across one or more local axes:

```sgsl
instance RightPump WaterPump
    at 12 0 -22
    rotate 0 -90 0
    mirror z
```

Accepted axis sets are:

```text
x y z xy xz yz xyz
```

Axis order in the source is not significant. Mirroring affects the complete
component instance, including child offsets and child rotations. Nested
mirrors compose through the component hierarchy.

## Transform order

An instance uses this transform order:

```text
parent * translation * rotation * mirror * uniform scale
```

The mirror therefore uses the instance's local axes and is applied before its
rotation. Anchors are resolved on individual objects before the instance
transform is applied.

## Renderer behavior

The expanded scene stores ordinary positions and rotations. Reflections cannot
be represented directly by a Roblox `CFrame`, so the expander selects an
equivalent proper rotation for each supported primitive after reflecting its
position. Symmetric primitives keep the same visible geometry. `pipeArc` uses
its local arc plane when choosing that equivalent rotation, so the complete
elbow is mirrored as one shape rather than rotating each generated segment in
place.
