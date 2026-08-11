# Markers

Markers are named points with position and orientation. They do not generate
geometry and have no built-in gameplay meaning.

```sgsl
marker Grip
    at 0 1.2 0
    rotate 0 0 90
```

Markers inherit component, instance, repeat, scale, and rotation transforms.
The HTML renderer includes them in the payload but hides them by default. Add
`?markers=1` to the preview URL to display their axes.

The GLB renderer writes markers as named nodes without a mesh. Runtime Lua may
assign meaning to a marker name, for example `Grip`, `BottleStand`, or
`BottleSlot1`. SGSL itself does not interpret those names.
