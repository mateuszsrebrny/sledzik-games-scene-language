# SGSL v1

SGSL is a small scene language for describing simple 3D geometry.

Current scope:
- Parse `.sgsl` files with Python and Lark.
- Build `preview/scene.json`.
- View the result in a static Three.js previewer.
- Support reusable `component` / `instance` scene fragments.
- Support `rotate` transforms on scene objects and instances.

Not in scope right now:
- Automatic publishing of generated assets to Roblox

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
docs/                    Language extensions and proposals
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
- `pipeArc`
- `mesh` groups inside components

Common properties:
- `at x y z`
- `anchor x y z`
- `rotate x y z`
- `color name-or-hex`
- `transparency value`
- `emissive value`

Instance properties:
- `at x y z`
- `rotate x y z`
- `mirror axes`
- `scale value`
- `emissive value`
- `set parameter expression`

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

Pipe arc properties:
- `pipeRadius value`
- `bendRadius value`
- `angle degrees`
- `segments integer`

Notes:
- `rotate` uses Euler angles in degrees in `X Y Z` order.
- `cylinder` is vertical along the Y axis.
- `frustum` is currently approximated by a stack of thin cylinders in both preview and Roblox output.
- `ring` is currently approximated by a ring of small block segments in both preview and Roblox output.
- `pipeArc` starts at `at`, initially follows `+X`, lies in the XY plane, and is approximated by short cylinders.

Language docs:
- [Rotation](docs/ROTATE.md)
- [Components](docs/COMPONENTS.md)
- [Nested components](docs/NESTED_COMPONENTS.md)
- [Pipe arcs](docs/PIPE_ARC.md)
- [Imports](docs/IMPORT.md)
- [Instance scale](docs/SCALE.md)
- [Instance mirroring](docs/MIRROR.md)
- [Emissive materials](docs/EMISSIVE.md)
- [Mesh groups and GLB export](docs/MESH_GROUPS.md)

Components may contain instances of other components. For example:

```sgsl
component Window
    instance Frame WindowFrame
        set frameWidth windowWidth

    block Glass
        at 0 0 0
        size windowWidth windowHeight 0.12
        color lightblue
```

Nested position and rotation are composed through the complete component tree.
Expanded objects use full names such as `Factory01.Hall01.Window01.Glass`.

SGSL files can import reusable component libraries. Paths are relative to the
file containing the import:

```sgsl
scene Factory

import "components/pipe_elbow.sgsl"

instance Outlet PipeElbow
    at 4 2 0
```

Imported files do not need a `scene` declaration. Imports are transitive,
deduplicated by canonical path, and checked for cycles and duplicate component
names.

Built-in color names:
- `black`
- `white`
- `gray`
- `lightgray`
- `blue`
- `darkgray`
- `steelgray`
- `lightblue`
- `green`
- `red`
- `orange`
- `yellow`
- `brown`
- `silver`

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

The live preview server can load a project-specific entry scene into the editor:

```bash
python preview_server.py \
  --default-source path/to/preview.sgsl \
  --library "path/to/**/*.sgsl"
```

Without `--default-source`, the editor loads `examples/primitives.sgsl`.

Generate Roblox Lua:

```bash
python build_roblox.py examples/factory.sgsl
```

This writes:

```text
build/factory.lua
```

Export one component as GLB. Geometry inside each `mesh` group is combined
into one GLB object; other primitives remain separate objects:

```bash
python build_glb.py components/bottle.sgsl --component Bottle --output build/Bottle.glb
```

Generate a Rojo-friendly ModuleScript:

```bash
python build_roblox.py examples/factory.sgsl --rojo-module
```

Module mode returns a function that accepts an optional parent, requires the shared primitives module, creates the scene under that parent, and returns the scene folder. The default builder require expression is:

```lua
game.ReplicatedStorage.SceneLanguagePrimitives
```

Override it when your Roblox project exposes the primitives somewhere else:

```bash
python build_roblox.py examples/factory.sgsl --rojo-module --builder-require game.ReplicatedStorage.Shared.SceneLanguagePrimitives
```

Try the primitives example:

```bash
python build_preview.py examples/primitives.sgsl
python build_roblox.py examples/primitives.sgsl
```

Start the live preview server:

```bash
python preview_server.py
```

Use a different port if needed:

```bash
python preview_server.py --port 8123
```

Allow imports from selected SGSL library files:

```bash
python preview_server.py --library components/*.sgsl
```

Multiple `--library` options and quoted glob patterns are supported:

```bash
python preview_server.py \
    --library "components/**/*.sgsl" \
    --library examples/shared.sgsl
```

Only files listed by `--library` may be imported by code entered in the live
editor. Imports may use a path relative to the directory where the server was
started. A bare filename such as `import "window.sgsl"` also works when that
filename uniquely identifies one library file. Transitive imports must also be
included in the library list.

Open:

```text
http://localhost:8000/preview/
```

## Notes

- `preview/index.html` contains the live SGSL textarea and viewer.
- `preview/scene.json` should be regenerated locally from SGSL sources.
- `build/*.lua` is generated from SGSL sources.
- JavaScript sends SGSL text to the Python preview server.
- The browser loads local Three.js files from `preview/vendor/`.
- Fully transparent objects are skipped by the viewer. Partially transparent
  objects do not write to the depth buffer, preventing them from masking other
  transparent geometry as the camera moves.
