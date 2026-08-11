# Profile Revolve

`profileRevolve` creates a rotational solid from an ordered list of
`(height, radius)` points.

```sgsl
profileRevolve Shell
    profile
        point 0.000 0.620
        point 2.015 0.620
        point 2.660 0.210
        point 2.858 0.210
    thickness 0.055
    segments 32
    color #bedcf0
    material glass
```

The default anchor is `center bottom center`; `at` identifies the base of the
profile. Heights must be strictly increasing. With `thickness`, the inner
radius is calculated as `outerRadius - thickness` at every profile point. This
is a radial wall thickness, not a geometric normal offset.

HTML and GLB share `profile_revolve_geometry.py`, which creates the outer and
inner surfaces plus the top and bottom rims as one continuous mesh. Roblox
cannot create a hollow Part mesh, so its renderer emits one stepped frustum
fallback for each profile span. It does not duplicate profile data.
