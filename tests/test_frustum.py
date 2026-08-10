import unittest
from textwrap import dedent

from sgsl.parser import parse_text
from sgsl.renderers.glb_renderer import _geometry
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class FrustumTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene Demo
        frustum Cone
            at 0 0 0
            radius_bottom 2
            radius_top 0.5
            height 4
            segments 12
            color gray
        """
    ).strip()

    def test_html_and_glb_use_one_shared_mesh(self):
        scene = parse_text(self.SOURCE)
        obj = scene["objects"][0]
        html_obj = render_html(scene)["objects"][0]
        self.assertEqual(html_obj["type"], "frustum")
        self.assertEqual((html_obj["vertices"], html_obj["indices"]), _geometry(obj))
        self.assertEqual(len(render_html(scene)["objects"]), 1)

    def test_roblox_keeps_stepped_fallback(self):
        source = render_roblox(parse_text(self.SOURCE))
        self.assertIn("makeSteppedFrustum", source)

    def test_zero_top_radius_forms_a_point(self):
        scene = parse_text(self.SOURCE.replace("radius_top 0.5", "radius_top 0"))
        html_obj = render_html(scene)["objects"][0]
        self.assertEqual(html_obj["type"], "frustum")
        self.assertEqual(max(vertex[1] for vertex in html_obj["vertices"]), 2)


if __name__ == "__main__":
    unittest.main()
