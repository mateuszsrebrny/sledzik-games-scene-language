import unittest
from textwrap import dedent

from sgsl.hollow_frustum_geometry import hollow_frustum_geometry
from sgsl.parser import SGSLValidationError, parse_text
from sgsl.renderers.glb_renderer import _geometry
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class HollowFrustumTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene Demo
        hollowFrustum Wall
            at 1 2 3
            outerBottomRadius 2
            outerTopRadius 1.5
            innerBottomRadius 1.5
            innerTopRadius 1
            height 4
            segments 8
            color gray
        """
    ).strip()

    def test_parses_and_defaults_segments(self):
        scene = parse_text(
            dedent(
                """
            scene Demo
            hollowFrustum Wall
                at 0 0 0
                outerBottomRadius 2
                outerTopRadius 1
                innerBottomRadius 1
                innerTopRadius 0.5
                height 3
                color gray
                """
            ).strip()
        )
        self.assertEqual(scene["objects"][0]["segments"], 24)

    def test_shared_geometry_is_used_by_html_and_glb(self):
        obj = parse_text(self.SOURCE)["objects"][0]
        expected = hollow_frustum_geometry(2, 1.5, 1.5, 1, 4, 8)
        html_obj = render_html(parse_text(self.SOURCE))["objects"][0]
        self.assertEqual(html_obj["vertices"], expected[0])
        self.assertEqual(html_obj["indices"], expected[1])
        self.assertEqual(_geometry(obj), expected)
        self.assertEqual(len(expected[0]), 32)
        self.assertEqual(len(expected[1]), 192)

    def test_roblox_uses_outer_frustum_fallback(self):
        source = render_roblox(parse_text(self.SOURCE))
        self.assertIn("makeSteppedFrustum", source)
        self.assertIn("2,", source)
        self.assertNotIn("innerBottomRadius", source)

    def test_rejects_invalid_radii_and_segments(self):
        for replacements in (
            (("outerBottomRadius 2", "outerBottomRadius 1"), ("innerBottomRadius 1.5", "innerBottomRadius 1")),
            (("outerTopRadius 1.5", "outerTopRadius 1"), ("innerTopRadius 1", "innerTopRadius 1")),
        ):
            source = self.SOURCE
            for old, new in replacements:
                source = source.replace(old, new)
            with self.assertRaises(SGSLValidationError):
                parse_text(source)
        source = self.SOURCE.replace("segments 8", "segments 2")
        with self.assertRaises(SGSLValidationError):
            parse_text(source)


if __name__ == "__main__":
    unittest.main()
