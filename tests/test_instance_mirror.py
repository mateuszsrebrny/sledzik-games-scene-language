import math
import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects


class InstanceMirrorTests(unittest.TestCase):
    def test_mirrors_local_positions_without_changing_dimensions(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Marker
                    block Body
                        at 1 2 3
                        size 4 5 6
                        color gray
                instance Reflected Marker
                    at 10 20 30
                    mirror xz
                """
            ).strip()
        )

        body = scene["objects"][0]
        self.assertEqual(body["position"], [9.0, 22.0, 27.0])
        self.assertEqual(body["size"], [4.0, 5.0, 6.0])

    def test_applies_mirror_before_instance_rotation(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Marker
                    block Body
                        at 2 0 1
                        size 1 1 1
                        color gray
                instance Reflected Marker
                    at 10 0 20
                    rotate 0 90 0
                    mirror z
                """
            ).strip()
        )

        position = scene["objects"][0]["position"]
        for actual, expected in zip(position, [9.0, 0.0, 18.0]):
            self.assertAlmostEqual(actual, expected)

    def test_nested_mirrors_compose(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Marker
                    block Body
                        at 1 2 3
                        size 1 1 1
                        color gray
                component Assembly
                    instance Inner Marker
                        mirror z
                instance Root Assembly
                    mirror xz
                """
            ).strip()
        )

        self.assertEqual(scene["objects"][0]["position"], [-1.0, 2.0, 3.0])

    def test_mirrors_pipe_arc_as_one_shape(self):
        source = dedent(
            """
            scene Demo
            component Elbow
                pipeArc Bend
                    at 1 2 3
                    pipeRadius 0.2
                    bendRadius 2
                    angle 90
                    segments 4
                    color gray
            instance Reflected Elbow
                at 10 20 30
                rotate 90 0 0
                mirror z
            """
        ).strip()

        segments = iter_render_objects(parse_text(source))
        self.assertEqual(len(segments), 4)

        # With Rx=90, mirrored local Z becomes the negative world Y offset.
        first = segments[0]["position"]
        local_midpoint = math.radians(90 / 4 * 0.5)
        expected = [
            10 + 1 + 2 * math.sin(local_midpoint),
            20 + 3,
            30 + 2 + 2 * (1 - math.cos(local_midpoint)),
        ]
        for actual, wanted in zip(first, expected):
            self.assertAlmostEqual(actual, wanted)

    def test_rejects_invalid_axis_sets(self):
        for axes in ("q", "xx", "xyq"):
            with self.subTest(axes=axes):
                with self.assertRaisesRegex(SGSLValidationError, "invalid mirror"):
                    parse_text(
                        dedent(
                            f"""
                            scene Demo
                            component Marker
                                block Body
                                    size 1 1 1
                                    color gray
                            instance Invalid Marker
                                mirror {axes}
                            """
                        ).strip()
                    )


if __name__ == "__main__":
    unittest.main()
