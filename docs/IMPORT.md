# Imports

## Goal

Allow components and scenes to be split across multiple `.sgsl` files.

This enables reusable component libraries without duplicating
definitions.

------------------------------------------------------------------------

## Syntax

``` sgsl
import "bottle.sgsl"
```

Paths are resolved relative to the importing file.

Example:

``` sgsl
import "../components/bottle.sgsl"
import "../components/bottle-shelf.sgsl"
```

------------------------------------------------------------------------

## File roles

Component files do not need to declare a scene.

Example:

``` sgsl
component Bottle
    ...
```

The entry file declares the scene:

``` sgsl
scene FactoryFlow

import "../components/bottle.sgsl"
import "../components/bottle-shelf.sgsl"

instance Shelf BottleShelf
    at 0 0 0
```

------------------------------------------------------------------------

## Semantics

-   Imports are processed before component expansion.
-   Imported component definitions become available to the importing
    file.
-   Import paths are resolved relative to the importing file.
-   Importing the same resolved file more than once must not duplicate
    definitions.
-   The parser should track imported files by canonical absolute path.
-   Component names must be unique across the complete import graph.
-   Duplicate component names are an error.
-   Import cycles are an error.
-   Imported files may import other files.
-   Only the entry file should normally declare `scene`.
-   Imported files may contain components, objects, and instances. Their
    statements are merged before the importing file's statements.
-   `parse_text()` cannot resolve imports because it has no base directory;
    use `parse_file()` or either build command.

------------------------------------------------------------------------

## Errors

Missing file:

``` text
Could not import '../components/bottle.sgsl'
from 'scenes/factory-flow.sgsl'.
```

Import cycle:

``` text
Import cycle detected:
a.sgsl -> b.sgsl -> a.sgsl
```

Duplicate component:

``` text
Component 'Bottle' is defined in both:
components/bottle.sgsl
components/legacy-bottle.sgsl
```

------------------------------------------------------------------------

## Suggested project layout

``` text
scene-language/
├── components/
│   ├── bottle.sgsl
│   └── bottle-shelf.sgsl
└── scenes/
    └── factory-flow.sgsl
```

------------------------------------------------------------------------

## Loading algorithm

1.  Resolve the entry file.
2.  Parse its imports.
3.  Resolve each import relative to the current file.
4.  Canonicalize the path.
5.  Skip files already loaded.
6.  Detect files currently on the import stack as cycles.
7.  Merge component definitions into one registry.
8.  Validate duplicate component names.
9.  Expand the entry scene.

------------------------------------------------------------------------

## Build example

Given this component library:

```sgsl
# components/elbow.sgsl
component Elbow
    pipeArc Bend
        at 0 0 0
        pipeRadius 0.2
        bendRadius 1.5
        angle 90
        segments 12
        color steelgray
```

an entry scene can import and instantiate it:

```sgsl
# scenes/pipes.sgsl
scene Pipes

import "../components/elbow.sgsl"

instance Outlet Elbow
    at 4 2 0
```

Build the entry file normally:

```bash
python build_preview.py scenes/pipes.sgsl
python build_roblox.py scenes/pipes.sgsl
```

------------------------------------------------------------------------

## Backward compatibility

Fully backward compatible.

Existing single-file scenes continue to work unchanged.
