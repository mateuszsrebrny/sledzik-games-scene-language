# SGSL v1

SGSL is a small scene language for describing simple 3D geometry.

Current scope:
- Parse `.sgsl` files with Python and Lark.
- Build `preview/scene.json`.
- View the result in a static Three.js previewer.

Not in scope right now:
- GLB export
- Groups
- Rotation

## Requirements

- Python 3
- `lark`

Install:

```bash
pip install -r sgsl/requirements.txt
```

## Project Layout

```text
build_preview.py          CLI entrypoint
build_roblox.py          Roblox Lua generator
examples/                 Example scenes
preview/index.html        Static viewer
preview/scene.json        Generated preview data (not committed)
preview/vendor/           Local Three.js files
sgsl/grammar.lark         Grammar
sgsl/parser.py            Parse + validate scene files
sgsl/transformer.py       Lark transformer
sgsl/renderers/html_renderer.py
```

## SGSL Example

```sgsl
scene Shapes

block Floor
    at 0 -0.15 0
    size 16 0.3 10
    color lightgray

cylinder Tank
    at -4 2 0
    radius 1.5
    height 4
    color blue

frustum Stack
    at 4 3 0
    radius_bottom 2
    radius_top 0.8
    height 6
    segments 12
    color darkgray
```

Supported object types:
- `block`
- `cylinder`
- `frustum`
- `ring`

Common properties:
- `at x y z`
- `anchor x y z`
- `color name-or-hex`
- `transparency value`

Block properties:
- `size x y z`

Cylinder properties:
- `radius value`
- `height value`

Frustum properties:
- `radius_bottom value`
- `radius_top value`
- `height value`
- `segments integer`

Ring properties:
- `radius_inner value`
- `radius_outer value`
- `height value`
- `segments integer`

Notes:
- `cylinder` is vertical along the Y axis.
- `frustum` is currently approximated by a stack of thin cylinders in both preview and Roblox output.
- `ring` is currently approximated by a ring of small block segments in both preview and Roblox output.

Built-in color names:
- `white`
- `gray`
- `lightgray`
- `blue`
- `darkgray`
- `steelgray`

## Build Preview

Generate preview data:

```bash
python build_preview.py examples/hall.sgsl
```

This writes:

```text
preview/scene.json
```

`preview/scene.json` is a generated build artifact and is not tracked in git.

Generate Roblox Lua:

```bash
python build_roblox.py examples/factory.sgsl
```

This writes:

```text
build/factory.lua
```

Try the primitives example:

```bash
python build_preview.py examples/primitives.sgsl
python build_roblox.py examples/primitives.sgsl
```

Start a local server:

```bash
python -m http.server
```

Open:

```text
If you run the server from the repository root:
http://localhost:8000/preview/

If you run the server from inside the preview directory:
http://localhost:8000/
```

## Notes

- `preview/index.html` is static.
- `preview/scene.json` should be regenerated locally from SGSL sources.
- `build/*.lua` is generated from SGSL sources.
- JavaScript does not parse SGSL directly.
- The browser loads local Three.js files from `preview/vendor/`.
