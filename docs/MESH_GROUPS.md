# Mesh groups

`mesh` marks geometry that may be compiled into one mesh asset:

```sgsl
component Bottle
    mesh Shell
        cylinder Body
            at 0 1 0
            radius 1
            height 2
            color white

        cylinder Neck
            at 0 2.3 0
            radius 0.4
            height 0.6
            color white
```

A mesh group may contain primitives and component instances. It supports `at`
and `rotate`; its transform is composed between the containing component and
its children.

The preview and Roblox Part renderer expand the children normally. The GLB
renderer combines all children into one GLB object named after the group.

The first implementation requires one color, transparency and emissive value
per mesh group. Split geometry into multiple groups when materials differ.

Export a component without adding a scene wrapper:

```bash
python build_glb.py components/bottle.sgsl \
  --component Bottle \
  --output build/Bottle.glb
```
