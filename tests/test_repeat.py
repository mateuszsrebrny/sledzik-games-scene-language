import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text


class RepeatTests(unittest.TestCase):
    def test_repeats_component_instances_along_a_step_vector(self):
        scene = parse_text(
            dedent("""
            scene Demo

            component Marker
                block Part
                    at 0 0 0
                    size 1 1 1
                    color white

            repeat Dash Marker
                count 3
                at -2 1 4
                step 2 0 -1
            """).strip()
        )

        self.assertEqual(
            [obj["name"] for obj in scene["objects"]],
            ["Dash01.Part", "Dash02.Part", "Dash03.Part"],
        )
        self.assertEqual(
            [obj["position"] for obj in scene["objects"]],
            [[-2.0, 1.0, 4.0], [0.0, 1.0, 3.0], [2.0, 1.0, 2.0]],
        )

    def test_supports_component_parameters_and_parent_rotation(self):
        scene = parse_text(
            dedent("""
            scene Demo

            component Marker
                block Part
                    at 0 0 0
                    size 1 1 1
                    color white

            component Road
                param dashCount 3
                param dashStep 2

                repeat Dash Marker
                    count dashCount
                    at 0 0 0
                    step dashStep 0 0

            instance RotatedRoad Road
                at 10 0 5
                rotate 0 90 0
            """).strip()
        )

        self.assertEqual(len(scene["objects"]), 3)
        for actual, expected in zip(
            [obj["position"] for obj in scene["objects"]],
            [[10.0, 0.0, 5.0], [10.0, 0.0, 3.0], [10.0, 0.0, 1.0]],
        ):
            for actual_axis, expected_axis in zip(actual, expected):
                self.assertAlmostEqual(actual_axis, expected_axis)

    def test_rejects_invalid_counts(self):
        template = """
            scene Demo
            component Marker
                block Part at 0 0 0 size 1 1 1 color white
            repeat Item Marker
                count {count}
                step 1 0 0
        """
        for count in ("-1", "1.5", "10001"):
            with self.subTest(count=count):
                with self.assertRaisesRegex(SGSLValidationError, "count"):
                    parse_text(dedent(template.format(count=count)).strip())


if __name__ == "__main__":
    unittest.main()
