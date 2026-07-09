# SGSL — Anchors v1

## Goal

Add a way to specify which point of a block is placed at the coordinates given by `at`.

Right now, `at` always means the center of the block:

```sgsl
block Example
    at 0 2 0
    size 4 4 4
    color white
```

After adding anchors, this must continue to work exactly the same way.

The new `anchor` property is optional.

---

# Backward compatibility

If an object does not define an `anchor`, assume:

```sgsl
anchor center center center
```

That is why all existing `.sgsl` files remain valid and keep the same geometry.

Equivalent examples:

```sgsl
block Example
    at 0 2 0
    size 4 4 4
    color white
```

```sgsl
block Example
    anchor center center center
    at 0 2 0
    size 4 4 4
    color white
```

---

# Syntax

```sgsl
anchor <x-anchor> <y-anchor> <z-anchor>
```

Allowed values:

## X Axis

```text
left
center
right
```

## Y Axis

```text
bottom
center
top
```

## Z Axis

```text
front
center
back
```

Full example:

```sgsl
block FrontWall
    anchor center bottom front
    at 0 0 -5
    size 16 7 0.35
    color white
```

---

# Coordinate System

SGSL uses the following convention:

```text
X = left / right
Y = down / up
Z = front / back
```

The front of the scene is on the negative Z side.

```text
front = -Z
back  = +Z
```

---

# Meaning of `at`

`at` defines the position of the point selected by `anchor`.

Example:

```sgsl
block Box
    anchor center bottom center
    at 0 0 0
    size 4 2 4
    color white
```

The bottom center of the block is at `(0, 0, 0)`.

So the actual center of the block is at:

```text
(0, 1, 0)
```

---

# Computing the Block Center

The renderer should first read:

```text
at = (atX, atY, atZ)
size = (sizeX, sizeY, sizeZ)
```

Then it should convert the chosen anchor into the block center position.

## X Axis

```text
left:
    centerX = atX + sizeX / 2

center:
    centerX = atX

right:
    centerX = atX - sizeX / 2
```

## Y Axis

```text
bottom:
    centerY = atY + sizeY / 2

center:
    centerY = atY

top:
    centerY = atY - sizeY / 2
```

## Z Axis

```text
front:
    centerZ = atZ + sizeZ / 2

center:
    centerZ = atZ

back:
    centerZ = atZ - sizeZ / 2
```

Result:

```text
position = (centerX, centerY, centerZ)
```

This is the position passed to Three.js, Roblox, and future renderers.

---

# Examples

## Placing a Block on the Floor

```sgsl
block Machine
    anchor center bottom center
    at 0 0 0
    size 4 3 2
    color gray
```

The block has its bottom at `Y = 0`.

Its center will be at:

```text
Y = 1.5
```

---

## Front Wall

```sgsl
block FrontWall
    anchor center bottom front
    at 0 0 -5
    size 16 7 0.35
    color white
```

The front face of the wall is exactly at:

```text
Z = -5
```

The wall extends toward the inside of the building, which is positive Z.

Wall center:

```text
(0, 3.5, -4.825)
```

---

## Back Wall

```sgsl
block BackWall
    anchor center bottom back
    at 0 0 5
    size 16 7 0.35
    color white
```

The back face of the wall is exactly at:

```text
Z = 5
```

The wall extends toward the interior, which is negative Z.

Wall center:

```text
(0, 3.5, 4.825)
```

---

## Left Wall

```sgsl
block LeftWall
    anchor left bottom center
    at -8 0 0
    size 0.35 7 10
    color white
```

The outer left face is at:

```text
X = -8
```

Wall center:

```text
(-7.825, 3.5, 0)
```

---

## Right Wall

```sgsl
block RightWall
    anchor right bottom center
    at 8 0 0
    size 0.35 7 10
    color white
```

The outer right face is at:

```text
X = 8
```

Wall center:

```text
(7.825, 3.5, 0)
```

---

## Roof Aligned by Its Top Surface

```sgsl
block Roof
    anchor center top center
    at 0 7 0
    size 15.3 0.3 9.3
    color lightgray
```

The top surface of the roof is at:

```text
Y = 7
```

Roof center:

```text
Y = 6.85
```

---

## Block Corner

```sgsl
block CornerBox
    anchor left bottom front
    at 0 0 0
    size 2 4 6
    color blue
```

The left, bottom, front corner is at `(0, 0, 0)`.

Block center:

```text
(1, 2, 3)
```

---

# Zmiany w gramatyce Lark

An optional `anchor` should be added to the `block` object properties.

Example rule:

```lark
property: at
        | size
        | color
        | anchor

anchor: "anchor" X_ANCHOR Y_ANCHOR Z_ANCHOR

X_ANCHOR: "left" | "center" | "right"
Y_ANCHOR: "bottom" | "center" | "top"
Z_ANCHOR: "front" | "center" | "back"
```

If the grammar ignores all whitespace, make sure the `center` token can appear in all three positions.

---

# Transformer

The transformer should store the anchor in the internal scene model, for example:

```python
anchor = ("left", "bottom", "front")
```

Default value:

```python
anchor = ("center", "center", "center")
```

It is best to set the default value when creating the `Block` object and then override it if an `anchor` property is present in the file.

---

# Model danych

Example object after parsing:

```json
{
  "type": "block",
  "name": "FrontWall",
  "at": [0, 0, -5],
  "size": [16, 7, 0.35],
  "color": "white",
  "anchor": ["center", "bottom", "front"]
}
```

The renderer may additionally compute a field such as:

```json
{
  "position": [0, 3.5, -4.825]
}
```

However, it should not replace the original `at`, because that may still be useful for debugging.

---

# Walidacja

The parser or validation stage should raise an error if:

- the X axis value is not one of `left`, `center`, `right`,
- the Y axis value is not one of `bottom`, `center`, `top`,
- the Z axis value is not one of `front`, `center`, `back`,
- one object contains more than one `anchor` property.

Invalid example:

```sgsl
anchor bottom left front
```

The first value always belongs to the X axis, so `bottom` is not allowed there.

---

# Renderers

Anchor resolution should happen in one shared place before passing the object to renderers.

Preferred pipeline:

```text
SGSL
  ↓
parser
  ↓
scene object with at, size, and anchor
  ↓
resolve_anchor()
  ↓
scene object with computed position
  ↓
HTML renderer / Roblox renderer
```

Anchor calculations should not be reimplemented separately in every renderer.

That ensures HTML and Roblox always receive identical geometry.

---

# Completion Criteria

The implementation is correct if:

1. Old files without `anchor` look exactly the same as before.
2. `anchor center center center` produces exactly the same result as no `anchor`.
3. The four walls in the test file have their outer faces exactly at:
   - X = -8,
   - X = 8,
   - Z = -5,
   - Z = 5.
4. All walls start exactly at Y = 0.
5. Wall corners meet without gaps.
6. The HTML renderer and the future Roblox renderer use the same computed positions.
