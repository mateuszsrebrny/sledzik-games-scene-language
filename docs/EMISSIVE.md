# emissive

Marks a primitive or component instance as self-illuminated.

`emissive` describes the visual appearance only. It does not specify how the renderer should implement the effect.

## Syntax

```sgsl
emissive <number>
```

Example:

```sgsl
block StatusLight
    at 0 1 0
    size 0.2 0.2 0.2
    color green
    emissive 1
```

## Parameters

`emissive`

- Type: floating-point number
- Range: `>= 0`
- Default: `0`

Suggested interpretation:

| Value | Meaning |
|------:|---------|
| 0 | No emission |
| 0.5 | Weak glow |
| 1 | Normal indicator LED |
| 2 | Bright light |
| 5+ | Very strong emission |

Renderers may map the intensity differently.

## Color

The emitted light uses the object's `color`.

Example:

```sgsl
color blue
emissive 2
```

produces a bright blue glowing object.

No separate `emissiveColor` property is defined.

## Renderer Notes

### HTML Renderer

Should use the rendering engine's emissive material support (for example, Three.js `emissive` and `emissiveIntensity`).

### Roblox Renderer

May map emissive objects to:

- `Enum.Material.Neon`
- Optional `PointLight` / `SurfaceLight` for higher emissive values.

The exact implementation is renderer-specific.

## Applicability

`emissive` may be used on all primitives and component instances.

It affects appearance only and has no impact on geometry, physics or gameplay.
