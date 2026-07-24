import math
import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects


class RingTests(unittest.TestCase):
    def _render(self, *, start_angle=None, angle=None, radius_inner=2, segments=4):
        optional = ""
        if start_angle is not None:
            optional += f"\n                    start_angle {start_angle}"
        if angle is not None:
            optional += f"\n                    angle {angle}"
        scene = parse_text(
            dedent(
                f"""
                scene Demo
                ring RoadCurve
                    at 0 0 0
                    radius_inner {radius_inner}
                    radius_outer 4
                    height 0.3
                    segments {segments}
                    color gray{optional}
                """
            ).strip()
        )
        return iter_render_objects(scene)

    def test_defaults_to_a_full_ring(self):
        objects = self._render()
        self.assertEqual(len(objects), 4)
        self.assertTrue(all(obj["type"] == "block" for obj in objects))

    def test_expands_only_the_requested_angular_slice(self):
        objects = self._render(start_angle=180, angle=90, segments=3)
        self.assertEqual(len(objects), 3)
        for obj in objects:
            self.assertLess(obj["position"][0], 0)
            self.assertLess(obj["position"][2], 0)

    def test_accepts_zero_inner_radius(self):
        objects = self._render(start_angle=0, angle=90, radius_inner=0)
        self.assertEqual(len(objects), 4)
        self.assertTrue(all(math.isclose(obj["size"][2], 4) for obj in objects))

    def test_rejects_invalid_angles(self):
        for angle in (0, 361, -361):
            with self.subTest(angle=angle):
                with self.assertRaises(SGSLValidationError):
                    self._render(angle=angle)


if __name__ == "__main__":
    unittest.main()
