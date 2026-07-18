import json
import struct
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_component_file, parse_file, parse_text
from sgsl.renderers.glb_renderer import write
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class MeshGroupTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene BottleScene
        component Detail
            cylinder Ring
                at 0 1 0
                radius 0.5
                height 0.2
                color white

        component Bottle
            mesh Shell
                at 2 0 0
                rotate 0 90 0
                cylinder Body
                    at 3 0 0
                    radius 1
                    height 2
                    color white
                instance Detail01 Detail

            cylinder Water
                at 0 1 0
                radius 0.8
                height 1.5
                color blue
            cylinder Cap
                at 0 2.2 0
                radius 0.5
                height 0.2
                color blue
            cylinder Label
                at 0 1 0
                radius 1.01
                height 0.5
                color red

        instance Bottle Bottle
            at 10 0 5
        """
    ).strip()

    def test_expands_mesh_children_with_group_transform_and_metadata(self):
        scene = parse_text(self.SOURCE)
        body = scene["objects"][0]
        self.assertEqual(body["name"], "Bottle.Body")
        self.assertEqual(body["mesh_group"], "Bottle.Shell")
        self.assertAlmostEqual(body["position"][0], 12)
        self.assertAlmostEqual(body["position"][2], 2)
        nested = scene["objects"][1]
        self.assertEqual(nested["mesh_group"], "Bottle.Shell")

    def test_existing_renderers_keep_mesh_children_as_primitives(self):
        scene = parse_text(self.SOURCE)
        self.assertEqual(len(render_html(scene)["objects"]), 5)
        lua = render_roblox(scene)
        self.assertIn("Bottle.Body", lua)
        self.assertIn("Bottle.Water", lua)

    def test_glb_merges_shell_and_preserves_dynamic_objects(self):
        scene = parse_text(self.SOURCE)
        with tempfile.TemporaryDirectory() as directory:
            path = write(scene, Path(directory) / "Bottle.glb")
            payload = _read_glb_json(path)
        self.assertEqual([node["name"] for node in payload["nodes"]], ["Shell", "Water", "Cap", "Label"])
        self.assertEqual(len(payload["meshes"]), 4)

    def test_repository_bottle_fixture_exports_four_named_objects(self):
        fixture = Path(__file__).with_name("scenes") / "bottle_mesh.sgsl"
        with tempfile.TemporaryDirectory() as directory:
            payload = _read_glb_json(write(parse_file(fixture), Path(directory) / "Bottle.glb"))
        self.assertEqual([node["name"] for node in payload["nodes"]], ["Shell", "Water", "Cap", "Label"])

    def test_rejects_multiple_materials_in_one_mesh(self):
        source = self.SOURCE.replace("color white", "color red", 1)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SGSLValidationError, "multiple materials"):
                write(parse_text(source), Path(directory) / "invalid.glb")

    def test_component_file_does_not_need_a_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bottle.sgsl"
            path.write_text(
                dedent(
                    """
                    component Bottle
                        mesh Shell
                            cylinder Handle
                                at 0 1 0
                                radius 1
                                height 2
                                color white
                        cylinder Water
                            at 0 1 0
                            radius 0.8
                            height 1.5
                            color blue
                    """
                ).strip(),
                encoding="utf-8",
            )
            # parse_file still enforces a scene for normal scene builds.
            with self.assertRaises(SGSLValidationError):
                parse_file(path)
            scene = parse_component_file(path, "Bottle")
            self.assertEqual(scene["scene"], "Bottle")
            self.assertEqual(scene["objects"][0]["mesh_group"], "Bottle.Shell")


def _read_glb_json(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert (magic, version, length) == (b"glTF", 2, len(data))
    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    assert chunk_type == b"JSON"
    return json.loads(data[20 : 20 + chunk_length])


if __name__ == "__main__":
    unittest.main()
