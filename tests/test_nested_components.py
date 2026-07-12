import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text


class NestedComponentTests(unittest.TestCase):
    def test_expands_nested_instances_with_full_names(self):
        scene = parse_text(
            dedent("""
            scene Demo

            component Window
                block Glass
                    at 0 0 0
                    size 3 2 0.1
                    color lightblue

            component Hall
                instance FrontWindow Window
                    at 4 5 -9

            instance Hall01 Hall
                at 20 0 10
            """).strip()
        )

        self.assertEqual(scene["objects"][0]["name"], "Hall01.FrontWindow.Glass")
        self.assertEqual(scene["objects"][0]["position"], [24.0, 5.0, 1.0])

    def test_composes_nested_position_and_rotation(self):
        scene = parse_text(
            dedent("""
            scene Demo

            component Marker
                block Part
                    at 1 0 0
                    size 1 1 1
                    rotate 20 0 10
                    color red

            component Assembly
                instance Marker01 Marker
                    at 2 0 0
                    rotate 0 90 0

            instance Root Assembly
                at 10 0 5
                rotate 0 90 0
            """).strip()
        )

        obj = scene["objects"][0]
        for actual, expected in zip(obj["position"], [9.0, 0.0, 3.0]):
            self.assertAlmostEqual(actual, expected)
        self.assertNotEqual(obj["rotation"], [20.0, 180.0, 10.0])

    def test_parent_parameters_can_override_nested_instance_parameters(self):
        scene = parse_text(
            dedent("""
            scene Demo

            component Window
                param windowWidth 2
                block Glass
                    at 0 0 0
                    size windowWidth 1 0.1
                    color lightblue

            component Hall
                param hallWindowWidth 4
                instance Window01 Window
                    at hallWindowWidth 0 0
                    set windowWidth hallWindowWidth

            instance Hall01 Hall
                at 1 0 0
                set hallWindowWidth 6
            """).strip()
        )

        obj = scene["objects"][0]
        self.assertEqual(obj["position"], [7.0, 0.0, 0.0])
        self.assertEqual(obj["size"], [6.0, 1.0, 0.1])

    def test_limits_recursive_component_expansion(self):
        with self.assertRaisesRegex(SGSLValidationError, "maximum nesting depth of 64"):
            parse_text(
                dedent("""
                scene Demo
                component Loop
                    instance Again Loop
                instance Root Loop
                """).strip()
            )


if __name__ == "__main__":
    unittest.main()
