import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text


class InstanceScaleTests(unittest.TestCase):
    def test_scales_dimensions_and_local_positions(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Bottle
                    block Body
                        at 2 4 0
                        size 2 6 2
                        color blue
                instance SmallBottle Bottle
                    at 10 1 0
                    scale 0.5
                """
            ).strip()
        )

        body = scene["objects"][0]
        self.assertEqual(body["position"], [11.0, 3.0, 0.0])
        self.assertEqual(body["size"], [1.0, 3.0, 1.0])

    def test_multiplies_nested_scales(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Part
                    cylinder Body
                        at 4 0 0
                        radius 2
                        height 8
                        color gray
                component Assembly
                    instance Inner Part
                        at 2 0 0
                        scale 0.5
                instance Outer Assembly
                    at 10 0 0
                    scale 0.5
                """
            ).strip()
        )

        body = scene["objects"][0]
        self.assertEqual(body["position"], [12.0, 0.0, 0.0])
        self.assertEqual(body["radius"], 0.5)
        self.assertEqual(body["height"], 2.0)

    def test_scale_expression_can_use_component_parameters(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Part
                    block Body
                        at 0 0 0
                        size 2 2 2
                        color red
                component Assembly
                    param childScale 0.25
                    instance Child Part
                        scale childScale
                instance Root Assembly
                    set childScale 0.75
                """
            ).strip()
        )

        self.assertEqual(scene["objects"][0]["size"], [1.5, 1.5, 1.5])

    def test_combines_scale_with_rotation(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Beam
                    block Body
                        at 2 0 0
                        size 4 2 2
                        rotate 0 0 15
                        color gray
                instance SmallBeam Beam
                    at 10 0 0
                    rotate 0 0 90
                    scale 0.5
                """
            ).strip()
        )

        body = scene["objects"][0]
        self.assertAlmostEqual(body["position"][0], 10.0)
        self.assertAlmostEqual(body["position"][1], 1.0)
        self.assertEqual(body["size"], [2.0, 1.0, 1.0])
        self.assertAlmostEqual(body["rotation"][2], 105.0)

    def test_rejects_non_positive_scale(self):
        for scale in (0, -1):
            with self.subTest(scale=scale):
                with self.assertRaisesRegex(SGSLValidationError, "expected a positive number"):
                    parse_text(
                        dedent(
                            f"""
                            scene Demo
                            component Part
                                block Body
                                    at 0 0 0
                                    size 1 1 1
                                    color gray
                            instance Invalid Part
                                scale {scale}
                            """
                        ).strip()
                    )


if __name__ == "__main__":
    unittest.main()
