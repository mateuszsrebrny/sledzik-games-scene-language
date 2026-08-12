import json
import struct
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from sgsl.parser import parse_text
from sgsl.primitives import iter_render_objects
from sgsl.renderers.glb_renderer import write as write_glb
from sgsl.renderers.html_renderer import render as render_html


class MarkerTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene MarkerDemo

        component Bottle
            marker Grip
                at 0 1.2 0
                rotate 0 0 90

        instance Main Bottle
            at 10 2 30
            rotate 0 45 0
            scale 2
        """
    ).strip()

    def test_marker_is_transformed_without_geometry(self):
        scene = parse_text(self.SOURCE)
        objects = iter_render_objects(scene)

        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["type"], "marker")
        self.assertEqual(objects[0]["name"], "Main.Grip")
        self.assertAlmostEqual(objects[0]["position"][0], 10)
        self.assertAlmostEqual(objects[0]["position"][1], 4.4)
        self.assertAlmostEqual(objects[0]["position"][2], 30)

    def test_html_payload_keeps_marker_metadata(self):
        payload = render_html(parse_text(self.SOURCE))

        self.assertEqual(payload["objects"][0]["type"], "marker")
        self.assertEqual(payload["objects"][0]["name"], "Main.Grip")
        for actual, expected in zip(payload["objects"][0]["rotation"], [0.0, 45.0, 90.0]):
            self.assertAlmostEqual(actual, expected)

    def test_glb_exports_marker_as_importable_transparent_mesh_node(self):
        with tempfile.TemporaryDirectory() as directory:
            output = write_glb(parse_text(self.SOURCE), Path(directory) / "markers.glb")
            data = output.read_bytes()

        json_length = struct.unpack_from("<I", data, 12)[0]
        payload = json.loads(data[20 : 20 + json_length].decode("utf-8"))
        marker_nodes = [node for node in payload["nodes"] if node["name"] == "Grip"]

        self.assertEqual(len(marker_nodes), 1)
        self.assertIn("mesh", marker_nodes[0])
        self.assertEqual(marker_nodes[0]["translation"], [10.0, 4.4, 30.0])
        self.assertEqual(marker_nodes[0]["extras"], {"sgslType": "marker"})
        marker_mesh = payload["meshes"][marker_nodes[0]["mesh"]]
        marker_material = payload["materials"][marker_mesh["primitives"][0]["material"]]
        self.assertEqual(marker_mesh["name"], "SGSLMarker")
        self.assertEqual(marker_material["alphaMode"], "BLEND")
        self.assertEqual(marker_material["pbrMetallicRoughness"]["baseColorFactor"][3], 0.0)
