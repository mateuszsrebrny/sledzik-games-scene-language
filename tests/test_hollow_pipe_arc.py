import unittest
from textwrap import dedent

from sgsl.hollow_pipe_arc_geometry import hollow_pipe_arc_geometry
from sgsl.parser import SGSLValidationError, parse_text
from sgsl.renderers.glb_renderer import _geometry
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class HollowPipeArcTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene Demo
        hollowPipeArc Corner
            at 0 0 0
            outerRadius 0.7
            innerRadius 0.48
            bendRadius 1.2
            startAngle 0
            angle 90
            crossStartAngle 0
            crossAngle 180
            segments 8
            color black
        """
    ).strip()

    def test_shared_geometry_is_used_by_html_and_glb(self):
        obj = parse_text(self.SOURCE)["objects"][0]
        expected = hollow_pipe_arc_geometry(0.7, 0.48, 1.2, 90, 8, 0, 0, 180)
        html_obj = render_html(parse_text(self.SOURCE))["objects"][0]
        self.assertEqual(html_obj["vertices"], expected[0])
        self.assertEqual(html_obj["indices"], expected[1])
        self.assertEqual(_geometry(obj), expected)
        self.assertEqual(len(expected[0]), 162)
        self.assertEqual(len(expected[1]), 960)

    def test_roblox_uses_segmented_cylinder_fallback(self):
        rendered = render_roblox(parse_text(self.SOURCE))
        self.assertGreater(rendered.count("Builder.makeCylinder("), 1)

    def test_rejects_invalid_radii_and_angles(self):
        for replacement in (
            ("outerRadius 0.7", "outerRadius 0.48"),
            ("angle 90", "angle 0"),
            ("crossAngle 180", "crossAngle 361"),
        ):
            with self.assertRaises(SGSLValidationError):
                parse_text(self.SOURCE.replace(replacement[0], replacement[1]))


if __name__ == "__main__":
    unittest.main()
