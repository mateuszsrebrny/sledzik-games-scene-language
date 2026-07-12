# Nested Components

Nested components allow an `instance` to appear inside another `component`.
They make it possible to build larger reusable objects from smaller ones while
keeping SGSL as the single source of geometry.

## Supported behavior

- Components may contain primitives and component instances.
- Instances may be nested to any practical depth.
- Every instance has a local position and rotation.
- Nested instances may override parameters with `set`.
- Parent parameters may be used in a nested instance's properties and `set`
  expressions.
- Expanded primitives receive their complete instance path as their name.
- Expansion is flattened before being passed to preview and Roblox renderers.

Expansion has a safety limit of 64 component levels. Exceeding it reports a
possible recursive component reference.

## Syntax

The syntax of an instance is identical at scene and component level:

```sgsl
instance <InstanceName> <ComponentName>
    at X Y Z
    rotate X Y Z
    set <ParameterName> <Expression>
```

For example, a window can contain a reusable frame:

```sgsl
scene NestedWindowDemo

component WindowFrame
    param frameWidth 4.0
    param frameHeight 6.0
    param frameThickness 0.35

    block Left
        at (-frameWidth / 2 + frameThickness / 2) 0 0
        size frameThickness frameHeight frameThickness
        color darkgray

    block Right
        at (frameWidth / 2 - frameThickness / 2) 0 0
        size frameThickness frameHeight frameThickness
        color darkgray

component Window
    param windowWidth 4.0
    param windowHeight 6.0
    param windowFrameThickness 0.35

    instance Frame WindowFrame
        set frameWidth windowWidth
        set frameHeight windowHeight
        set frameThickness windowFrameThickness

    block Glass
        at 0 0 0
        size (windowWidth - 2 * windowFrameThickness) (windowHeight - 2 * windowFrameThickness) 0.12
        color lightblue
        transparency 0.45

instance FrontWindow Window
    at 0 5 -9
```

The `Window` component evaluates its own parameters first. Their values are
then available while evaluating the nested `Frame` instance and its `set`
expressions.

## Local coordinate systems

Each component has its own local coordinate system. A nested instance is
positioned relative to the origin of its parent component.

```sgsl
component Marker
    block Part
        at 1 0 0
        size 1 1 1
        color red

component Assembly
    instance Marker01 Marker
        at 4 0 0

instance Root Assembly
    at 20 0 10
```

The resulting world position of `Part` is `(25, 0, 10)`.

## Transform composition

Transforms are composed in tree order:

```text
worldTransform =
    parentWorldTransform
    * instanceLocalTransform
    * primitiveLocalTransform
```

Positions and Euler angles are not added independently. SGSL composes complete
transformation matrices and only then extracts the final world position and
rotation consumed by renderers. Rotating a parent therefore changes both the
positions and orientations of all descendants.

This is equivalent to Roblox `CFrame` composition:

```lua
local worldCFrame = parentCFrame * instanceLocalCFrame * objectLocalCFrame
```

The preview and Roblox backends receive the same flattened world transforms.

## Parameters

For every component instance, expansion follows this order:

1. Evaluate the component's default parameters.
2. Evaluate and apply overrides from `set`.
3. Evaluate primitive properties in the component's parameter context.
4. Evaluate nested instance properties in the parent component's context.
5. Recursively expand nested instances.

Parent parameters may be passed to child parameters:

```sgsl
component Hall
    param hallWindowWidth 4.0

    instance Window01 Window
        at 0 5 -9
        set windowWidth hallWindowWidth
```

The first version does not provide parameter namespaces or shadowing rules.
Use distinctive parameter names across a nested component tree. Syntax such as
`set Window01.width 4` is not supported.

## Expanded names

Every primitive receives its full logical path. Given this hierarchy:

```text
Factory01
└── Hall01
    └── Window01
        └── Glass
```

the expanded primitive is named:

```text
Factory01.Hall01.Window01.Glass
```

The full path is preserved in preview JSON and generated Roblox part names.

## Current limitations

- Component expansion is flattened; renderers do not create a group/model for
  each logical instance.
- Parameter namespaces and explicit parent/child scope syntax are unavailable.
- Component bounding boxes and component-level anchors are unavailable.
- Recursive references are stopped by the depth limit rather than a full cycle
  detector.
