import json
import struct
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from textwrap import dedent

from sgsl.frustum_geometry import frustum_geometry
from sgsl.hollow_frustum_geometry import hollow_frustum_geometry
from sgsl.hollow_pipe_arc_geometry import hollow_pipe_arc_geometry
from sgsl.mesh_orientation import orient_outward, signed_volume
from sgsl.parser import parse_text
from sgsl.pipe_arc_geometry import pipe_arc_geometry
from sgsl.profile_revolve_geometry import profile_revolve_geometry
from sgsl.renderers.glb_renderer import _block_geometry, _cylinder_geometry, _wedge_geometry, write
from sgsl.sphere_geometry import sphere_geometry
from sgsl.spherical_cap_geometry import spherical_cap_geometry

# Roblox draws only a triangle's front face and ignores glTF's doubleSided, so
# a mesh wound inward renders inside out: the near wall disappears and the far
# wall's interior shows through it. Every revolved primitive shipped that way
# for months - trees and bushes you could see into - while the preview and any
# glTF viewer, which honour doubleSided, showed nothing wrong. These tests pin
# the property directly instead of trusting a viewer.
GENERATORS = {
    "block": lambda: _block_geometry([2, 3, 4]),
    "wedge": lambda: _wedge_geometry([2, 3, 4]),
    "cylinder": lambda: _cylinder_geometry(1.0, 2.0, 24),
    "frustum": lambda: frustum_geometry(2.0, 1.0, 2.0, 24),
    "frustum widening upward": lambda: frustum_geometry(1.0, 2.0, 2.0, 24),
    "frustum to a point": lambda: frustum_geometry(5.87, 0.02, 14.48, 48),
    "sphericalCap": lambda: spherical_cap_geometry(2.0, 1.5, 10),
    "sphere": lambda: sphere_geometry(1.5, 16),
    "hollowFrustum full": lambda: hollow_frustum_geometry(2.0, 1.6, 1.5, 1.2, 2.0, 24),
    "hollowFrustum 120": lambda: hollow_frustum_geometry(2.0, 1.6, 1.5, 1.2, 2.0, 24, 0.0, 120.0),
    "hollowFrustum -120": lambda: hollow_frustum_geometry(2.0, 1.6, 1.5, 1.2, 2.0, 24, 30.0, -120.0),
    "pipeArc +90": lambda: pipe_arc_geometry(0.3, 2.0, 90.0, 16),
    "pipeArc -90": lambda: pipe_arc_geometry(0.3, 2.0, -90.0, 16),
    "hollowPipeArc +90": lambda: hollow_pipe_arc_geometry(0.4, 0.3, 2.0, 90.0, 16),
    "hollowPipeArc -90": lambda: hollow_pipe_arc_geometry(0.4, 0.3, 2.0, -90.0, 16),
    "hollowPipeArc reversed cross": lambda: hollow_pipe_arc_geometry(0.4, 0.3, 2.0, 90.0, 16, 0.0, 180.0, -180.0),
    "profileRevolve bottom-up": lambda: profile_revolve_geometry([(0, 1.0), (2, 1.0), (3, 0.4)], 24),
    "profileRevolve top-down": lambda: profile_revolve_geometry([(3, 0.4), (2, 1.0), (0, 1.0)], 24),
    "profileRevolve with wall": lambda: profile_revolve_geometry([(0, 1.0), (2, 1.0), (3, 0.4)], 24, 0.1),
}


def _directed_edge_problems(vertices, indices):
    """Count edges that betray an inconsistent or open surface.

    Coincident vertices are welded first, because seams and per-ring copies
    are legitimate. On a closed surface wound one way throughout, every
    directed edge then occurs exactly once and is matched by its reverse.
    """
    welded = {}
    remap = [welded.setdefault(tuple(round(c, 6) for c in v), len(welded)) for v in vertices]
    edges = Counter()
    for offset in range(0, len(indices), 3):
        a, b, c = (remap[i] for i in indices[offset : offset + 3])
        if len({a, b, c}) < 3:
            continue
        for edge in ((a, b), (b, c), (c, a)):
            edges[edge] += 1
    repeated = sum(1 for count in edges.values() if count > 1)
    unmatched = sum(1 for (a, b) in edges if (b, a) not in edges)
    return repeated, unmatched


def _read_glb(path):
    data = Path(path).read_bytes()
    json_length = struct.unpack_from("<I", data, 12)[0]
    payload = json.loads(data[20 : 20 + json_length])
    offset = 20 + json_length
    binary_length = struct.unpack_from("<I", data, offset)[0]
    return payload, data[offset + 8 : offset + 8 + binary_length]


def _accessor(payload, binary, index):
    accessor = payload["accessors"][index]
    view = payload["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    width = {"SCALAR": 1, "VEC3": 3}[accessor["type"]]
    fmt = {5126: "f", 5125: "I", 5123: "H"}[accessor["componentType"]]
    values = struct.unpack_from(f"<{accessor['count'] * width}{fmt}", binary, start)
    if width == 1:
        return list(values)
    return [tuple(values[i : i + width]) for i in range(0, len(values), width)]


class GeneratorOrientationTests(unittest.TestCase):
    def test_every_generator_faces_out(self):
        for name, build in GENERATORS.items():
            with self.subTest(name):
                vertices, indices = build()
                self.assertGreater(signed_volume(vertices, indices), 0, f"{name} is wound inside out")

    def test_every_generator_is_closed_and_wound_one_way(self):
        # A positive total volume alone would let a few backwards triangles -
        # an end cap, say - hide inside an otherwise correct mesh.
        for name, build in GENERATORS.items():
            with self.subTest(name):
                repeated, unmatched = _directed_edge_problems(*build())
                self.assertEqual((repeated, unmatched), (0, 0), f"{name} has inconsistent or open edges")


class OrientOutwardTests(unittest.TestCase):
    def test_flips_a_mesh_wound_inward(self):
        vertices, indices = _block_geometry([1, 1, 1])
        inward = []
        for offset in range(0, len(indices), 3):
            inward.extend((indices[offset], indices[offset + 2], indices[offset + 1]))
        self.assertLess(signed_volume(vertices, inward), 0)
        self.assertGreater(signed_volume(vertices, orient_outward(vertices, inward)), 0)

    def test_leaves_a_mesh_wound_outward_untouched(self):
        vertices, indices = _block_geometry([1, 1, 1])
        self.assertEqual(orient_outward(vertices, indices), list(indices))


class ExportedOrientationTests(unittest.TestCase):
    """The same property on what Roblox actually imports.

    Goes through parse_text and write(), so it covers what happens after the
    generators: baked rotations, nested and mirrored instances. A mirror only
    reflects where a part sits, never the part itself, which is why it cannot
    turn a solid inside out - this pins that too.
    """

    SOURCE = dedent(
        """
        scene S
        component Plant
            cylinder Trunk
                at 0 0 0
                anchor center bottom center
                radius 0.5
                height 3
                color brown

            frustum Crown
                at 0 3 0
                anchor center bottom center
                radius_bottom 3
                radius_top 0.02
                height 6
                segments 24
                color green

            sphericalCap Bush
                at 3 0 0
                anchor center bottom center
                baseRadius 2
                height 1.5
                segments 10
                color green

            pipeArc Hose
                at -3 0 0
                pipeRadius 0.2
                bendRadius 1
                angle 120
                segments 12
                color gray
                rotate 0 0 30

        instance Plain Plant
            at 0 0 0

        instance Turned Plant
            at 20 0 0
            rotate 15 70 -20

        instance Reflected Plant
            at -20 0 0
            mirror x
        """
    ).strip() + "\n"

    def test_every_exported_mesh_faces_out(self):
        scene = parse_text(self.SOURCE)
        with tempfile.TemporaryDirectory() as directory:
            payload, binary = _read_glb(write(scene, Path(directory) / "plants.glb"))
        checked = 0
        for mesh in payload["meshes"]:
            if mesh["name"] == "SGSLMarker" or mesh["name"].startswith("SGSLVersion"):
                continue
            for primitive in mesh["primitives"]:
                vertices = _accessor(payload, binary, primitive["attributes"]["POSITION"])
                indices = _accessor(payload, binary, primitive["indices"])
                with self.subTest(mesh["name"]):
                    self.assertGreater(signed_volume(vertices, indices), 0, f"{mesh['name']} exported inside out")
                checked += 1
        self.assertGreaterEqual(checked, 12)


if __name__ == "__main__":
    unittest.main()
