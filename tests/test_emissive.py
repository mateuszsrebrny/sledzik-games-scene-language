import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class EmissiveTests(unittest.TestCase):
    def test_defaults_to_zero_and_is_included_in_preview(self):
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

        self.assertEqual(scene["objects"][0]["emissive"], 0.0)
        self.assertEqual(render_html(scene)["objects"][0]["emissive"], 0.0)

    def test_accepts_expressions_and_rejects_negative_values(self):
        valid = parse_text(
            dedent(
                """
                scene Demo
                block Light
                    at 0 0 0
                    size 1 1 1
                    color green
                    emissive 1 + 0.5
                """
            ).strip()
        )
        self.assertEqual(valid["objects"][0]["emissive"], 1.5)

        with self.assertRaisesRegex(SGSLValidationError, "non-negative"):
            parse_text(
                dedent(
                    """
                    scene Demo
                    block Invalid
                        at 0 0 0
                        size 1 1 1
                        color red
                        emissive -1
                    """
                ).strip()
            )

    def test_instance_emissive_applies_to_expanded_objects(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Lamp
                    block Shade
                        at 0 0 0
                        size 1 1 1
                        color yellow
                    cylinder Bulb
                        at 0 1 0
                        radius 0.2
                        height 0.4
                        color white
                        emissive 0.5

                instance Lamp01 Lamp
                    emissive 2
                """
            ).strip()
        )

        self.assertEqual([obj["emissive"] for obj in scene["objects"]], [2.0, 2.0])

    def test_nested_instance_can_override_parent_emissive(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Light
                    block Bulb
                        at 0 0 0
                        size 1 1 1
                        color blue

                component Pair
                    instance Left Light
                    instance Right Light
                        emissive 3

                instance Pair01 Pair
                    emissive 1
                """
            ).strip()
        )

        self.assertEqual([obj["emissive"] for obj in scene["objects"]], [1.0, 3.0])

    def test_expanded_primitives_keep_emissive_and_roblox_uses_neon(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                pipeArc GlowPipe
                    at 0 0 0
                    pipeRadius 0.1
                    bendRadius 1
                    angle 90
                    segments 3
                    color blue
                    emissive 2
                """
            ).strip()
        )

        self.assertTrue(all(obj["emissive"] == 2.0 for obj in iter_render_objects(scene)))
        self.assertIn("Enum.Material.Neon", render_roblox(scene))


if __name__ == "__main__":
    unittest.main()
