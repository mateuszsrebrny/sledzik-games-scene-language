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
