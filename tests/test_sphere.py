import json
import tempfile
import unittest
from textwrap import dedent
from pathlib import Path

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.glb_renderer import write as write_glb
from sgsl.renderers.roblox_renderer import render as render_roblox
from sgsl.sphere_geometry import sphere_geometry


class SphereTests(unittest.TestCase):
    def _scene(self, segments=12, radius=2.0):
        return parse_text(
            dedent(
                f"""
                scene Demo
                sphere Ball
                    at 0 0 0
                    radius {radius}
                    segments {segments}
                    color green
                """
            ).strip()
        )

    def test_html_keeps_sphere_as_one_mesh(self):
        objects = render_html(self._scene())["objects"]
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["type"], "sphere")
        self.assertGreater(len(objects[0]["vertices"]), 0)
        self.assertGreater(len(objects[0]["indices"]), 0)

    def test_overlapping_spheres_are_opaque_by_default(self):
        scene = parse_text(
            dedent(
                """
                scene Overlap
                sphere Front
                    at 0 0 0
                    radius 2
                    color green
                sphere Rear
                    at 1.5 0 1.2
                    radius 2
                    color blue
                """
            ).strip()
        )
        self.assertEqual(scene["objects"][0]["transparency"], 0.0)
        self.assertEqual(scene["objects"][1]["transparency"], 0.0)
        self.assertEqual(render_html(scene)["objects"][0]["transparency"], 0.0)

    def test_glb_default_sphere_material_is_opaque(self):
        with tempfile.TemporaryDirectory() as directory:
            output = write_glb(self._scene(), Path(directory) / "sphere.glb")
            data = output.read_bytes()
            json_length = int.from_bytes(data[12:16], "little")
            document = json.loads(data[20 : 20 + json_length])
            self.assertEqual(document["materials"][0]["alphaMode"], "OPAQUE")

    def test_mesh_normals_face_outward(self):
        vertices, indices = sphere_geometry(2, 12)
        for offset in range(0, len(indices), 3):
            a, b, c = (vertices[indices[offset + index]] for index in range(3))
            ab = [b[index] - a[index] for index in range(3)]
            ac = [c[index] - a[index] for index in range(3)]
            normal = [
                ab[1] * ac[2] - ab[2] * ac[1],
                ab[2] * ac[0] - ab[0] * ac[2],
                ab[0] * ac[1] - ab[1] * ac[0],
            ]
            midpoint = [(a[index] + b[index] + c[index]) / 3 for index in range(3)]
            self.assertGreater(sum(normal[index] * midpoint[index] for index in range(3)), 0)

    def test_roblox_uses_stepped_fallback(self):
        source = render_roblox(self._scene())
        self.assertIn("makeSteppedFrustum", source)
        self.assertNotIn("Unsupported render object type", source)

    def test_rejects_invalid_radius_or_segments(self):
        for source in (
            """
            scene Demo
            sphere Invalid
                at 0 0 0
                radius 0
                segments 8
                color green
            """,
            """
            scene Demo
            sphere Invalid
                at 0 0 0
                radius 1
                segments 2
                color green
            """,
        ):
            with self.subTest(source=source):
                with self.assertRaises(SGSLValidationError):
                    parse_text(dedent(source).strip())


if __name__ == "__main__":
    unittest.main()
