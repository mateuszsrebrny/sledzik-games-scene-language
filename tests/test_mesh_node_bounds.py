import json
import unittest
from textwrap import dedent

from sgsl.parser import parse_text
from sgsl.renderers.glb_renderer import mesh_node_bounds


class MeshNodeBoundsTests(unittest.TestCase):
    def test_reports_the_bounding_box_of_a_whole_mesh_group(self):
        # write() bakes every object's transform into its group's vertex data
        # and emits the node itself untransformed, so a consumer that needs to
        # know where the imported part lands has to measure the vertices. Here
        # the group spans y 0..3 while neither member is centred on that.
        scene = parse_text(
            dedent(
                """
                scene S
                component C
                    mesh Shell
                        cylinder Base
                            at 0 0 0
                            anchor center bottom center
                            radius 1
                            height 1
                            color white

                        cylinder Neck
                            at 0 1 0
                            anchor center bottom center
                            radius 0.25
                            height 2
                            color white

                instance C C
                """
            ).strip()
            + "\n"
        )
        bounds = mesh_node_bounds(scene)

        self.assertIn("Shell", bounds)
        self.assertAlmostEqual(bounds["Shell"]["min"][1], 0.0, places=6)
        self.assertAlmostEqual(bounds["Shell"]["max"][1], 3.0, places=6)
        self.assertAlmostEqual(bounds["Shell"]["center"][1], 1.5, places=6)
        self.assertAlmostEqual(bounds["Shell"]["size"][1], 3.0, places=6)

    def test_center_is_not_the_authored_position_for_offset_geometry(self):
        # The distinction the caller actually depends on: a bottom-anchored
        # primitive is authored at its base but imports centred on its middle.
        scene = parse_text(
            dedent(
                """
                scene S
                component C
                    cylinder Body
                        at 0 0 0
                        anchor center bottom center
                        radius 1
                        height 4
                        color white

                instance C C
                """
            ).strip()
            + "\n"
        )

        self.assertAlmostEqual(mesh_node_bounds(scene)["Body"]["center"][1], 2.0, places=6)

    def test_excludes_markers(self):
        scene = parse_text(
            dedent(
                """
                scene S
                component C
                    marker Grip
                        at 0 5 0

                    block Body
                        at 0 0 0
                        size 1 1 1
                        color white

                instance C C
                """
            ).strip()
            + "\n"
        )
        bounds = mesh_node_bounds(scene)

        self.assertNotIn("Grip", bounds)
        self.assertIn("Body", bounds)


if __name__ == "__main__":
    unittest.main()


class NodeNameUniquenessTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene S
        component Slat
            block Body
                at 0 0 0
                size 1 1 1
                color white

        component Crate
            instance SlatA Slat
                at 0 0 0
            instance SlatB Slat
                at 2 0 0
            instance SlatC Slat
                at 4 0 0

            marker Grip
                at 0 1 0

        instance Crate Crate
        """
    ).strip() + "\n"

    def _node_names(self):
        import struct
        import tempfile
        from pathlib import Path

        from sgsl.renderers.glb_renderer import write

        scene = parse_text(self.SOURCE)
        with tempfile.TemporaryDirectory() as directory:
            path = write(scene, Path(directory) / "Crate.glb")
            data = Path(path).read_bytes()
        length, = struct.unpack_from("<I", data, 12)
        return [node["name"] for node in json.loads(data[20:20 + length])["nodes"]]

    def test_gives_every_node_a_unique_name(self):
        names = self._node_names()

        self.assertEqual(len(names), len(set(names)), names)

    def test_leaves_the_first_use_of_a_name_untouched(self):
        # Existing exact-name lookups and required-part contracts point at the
        # bare name, so only the later collisions may be renamed.
        names = self._node_names()

        self.assertIn("Body", names)
        self.assertIn("Body_2", names)
        self.assertIn("Body_3", names)
        self.assertIn("Grip", names)
