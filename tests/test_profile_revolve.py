import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.profile_revolve_geometry import profile_revolve_geometry
from sgsl.renderers.glb_renderer import _geometry
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class ProfileRevolveTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene Demo
        profileRevolve Shell
            at 1 2 3
            segments 8
            profile
                point 0 2
                point 2 2
                point 4 1
            thickness 0.25
            color gray
        """
    ).strip()

    def test_profile_is_a_single_shared_hollow_mesh(self):
        scene = parse_text(self.SOURCE)
        obj = scene["objects"][0]
        expected = profile_revolve_geometry([[0, 2], [2, 2], [4, 1]], 8, 0.25)
        html_obj = render_html(scene)["objects"][0]
        self.assertEqual(html_obj["vertices"], expected[0])
        self.assertEqual(html_obj["indices"], expected[1])
        self.assertEqual(_geometry(obj), expected)
        self.assertEqual(obj["anchor"], ["center", "bottom", "center"])

    def test_thickness_is_optional_and_creates_a_solid_mesh(self):
        source = self.SOURCE.replace("            thickness 0.25\n", "")
        scene = parse_text(source)
        vertices, indices = profile_revolve_geometry([[0, 2], [2, 2], [4, 1]], 8)
        self.assertEqual(len(scene["objects"][0]["profile"]), 3)
        self.assertEqual(len(vertices), 26)
        self.assertEqual(len(indices), 144)

    def test_roblox_uses_profile_spans_without_copying_profile_data(self):
        rendered = render_roblox(parse_text(self.SOURCE))
        self.assertEqual(rendered.count("Builder.makeSteppedFrustum("), 3)
        self.assertIn("Shell_segment_01", rendered)
        self.assertIn("Shell_segment_02", rendered)

    def test_rejects_invalid_profile(self):
        for replacement in (
            ("point 2 2", "point 0 2"),
            ("thickness 0.25", "thickness 2"),
            ("segments 8", "segments 2"),
        ):
            with self.subTest(replacement=replacement):
                with self.assertRaises(SGSLValidationError):
                    parse_text(self.SOURCE.replace(*replacement))


if __name__ == "__main__":
    unittest.main()
