import math
import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


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
        self.assertEqual(len(objects), 12)
        self.assertEqual([obj["type"] for obj in objects[:3]], ["block", "wedge", "wedge"])

    def test_expands_only_the_requested_angular_slice(self):
        objects = self._render(start_angle=180, angle=90, segments=3)
        self.assertEqual(len(objects), 9)
        for obj in objects:
            self.assertLessEqual(obj["position"][0], 1e-9)
            self.assertLessEqual(obj["position"][2], 1e-9)

    def test_accepts_zero_inner_radius(self):
        objects = self._render(start_angle=0, angle=90, radius_inner=0)
        self.assertEqual(len(objects), 8)
        self.assertTrue(all(obj["type"] == "wedge" for obj in objects))
        expected_depth = 4 * math.cos(math.radians(90 / 4 / 2))
        self.assertTrue(all(math.isclose(obj["size"][2], expected_depth) for obj in objects))

    def test_preview_and_roblox_use_the_same_expanded_parts(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                ring Curve
                    at 1 2 3
                    radius_inner 2
                    radius_outer 5
                    height 0.3
                    start_angle 45
                    angle 90
                    segments 3
                    color gray
                """
            ).strip()
        )
        preview = render_html(scene)["objects"]
        roblox = render_roblox(scene)
        self.assertEqual(len(preview), 9)
        for obj in preview:
            builder = "makeWedge" if obj["type"] == "wedge" else "makeBlock"
            self.assertIn(builder, roblox)
            self.assertIn(obj["name"], roblox)

    def test_rejects_invalid_angles(self):
        for angle in (0, 361, -361):
            with self.subTest(angle=angle):
                with self.assertRaises(SGSLValidationError):
                    self._render(angle=angle)


if __name__ == "__main__":
    unittest.main()
