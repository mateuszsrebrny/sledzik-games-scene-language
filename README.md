# SGSL v1

SGSL is a small scene language for describing simple 3D block geometry.

Current scope:
- Parse `.sgsl` files with Python and Lark.
- Build `preview/scene.json`.
- View the result in a static Three.js previewer.

Not in scope right now:
- Roblox export
- GLB export
- Cylinders
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
scene MainFactory

block Floor
    at 0 -0.15 0
    size 16 0.3 10
    color lightgray
```

Supported object type:
- `block`

Supported properties:
- `at x y z`
- `size x y z`
- `color name-or-hex`

Built-in color names:
- `white`
- `gray`
- `lightgray`
- `blue`

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
