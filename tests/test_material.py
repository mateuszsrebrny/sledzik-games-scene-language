import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class MaterialTests(unittest.TestCase):
    def test_defaults_to_auto_for_backward_compatibility(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                block Plain
                    at 0 0 0
                    size 1 1 1
                    color white
                """
            ).strip()
        )

        self.assertEqual(scene["objects"][0]["material"], "auto")
        self.assertEqual(render_html(scene)["objects"][0]["material"], "auto")

    def test_explicit_material_reaches_expanded_objects_and_roblox(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                ring GlassRing
                    at 0 0 0
                    radius_inner 1
                    radius_outer 2
                    height 0.2
                    segments 8
                    color blue
                    material glass
                    transparency 0.4
                """
            ).strip()
        )

        self.assertTrue(all(obj["material"] == "glass" for obj in iter_render_objects(scene)))
        self.assertIn("Enum.Material.Glass", render_roblox(scene))

    def test_explicit_smooth_plastic_is_not_inferred_as_glass(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                cylinder Water
                    at 0 0 0
                    radius 1
                    height 2
                    color blue
                    material smoothPlastic
                    transparency 0.4
                """
            ).strip()
        )

        self.assertIn("Enum.Material.SmoothPlastic", render_roblox(scene))

    def test_rejects_unknown_material(self):
        with self.assertRaisesRegex(SGSLValidationError, "unsupported material"):
            parse_text(
                dedent(
                    """
                    scene Demo
                    block Invalid
                        at 0 0 0
                        size 1 1 1
                        color red
                        material marble
                    """
                ).strip()
            )

    def test_maps_city_materials_to_native_roblox_materials(self):
        for material, roblox_name in (
            ("asphalt", "Asphalt"),
            ("pavement", "Pavement"),
            ("concrete", "Concrete"),
            ("cobblestone", "Cobblestone"),
        ):
            scene = parse_text(
                dedent(
                    f"""
                    scene Demo
                    block Surface
                        at 0 0 0
                        size 1 1 1
                        color gray
                        material {material}
                    """
                ).strip()
            )
            self.assertIn(f"Enum.Material.{roblox_name}", render_roblox(scene))


if __name__ == "__main__":
    unittest.main()
