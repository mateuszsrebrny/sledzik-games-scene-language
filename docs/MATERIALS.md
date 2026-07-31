# Materials

`material` selects the intended surface family independently from color,
transparency, and emissive strength.

```sgsl
material auto
material smoothPlastic
material glass
material neon
material asphalt
material pavement
material concrete
material cobblestone
```

`auto` is the default and preserves the original renderer inference:
emissive objects become neon in Roblox, transparent objects become glass, and
the remaining objects use smooth plastic.

Explicit materials are useful when transparency does not imply glass:

```sgsl
cylinder Water
    at 0 1 0
    radius 0.5
    height 2
    color #4c98f7
    material smoothPlastic
    transparency 0.38
```

Renderers map these portable material families to their closest native
equivalent. Engine-specific properties such as Roblox `Reflectance` are not
part of this contract.
