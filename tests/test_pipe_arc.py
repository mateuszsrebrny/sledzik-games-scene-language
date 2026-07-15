import math
import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects


class PipeArcTests(unittest.TestCase):
    def _render(self, angle=90, rotation="0 0 0"):
        scene = parse_text(
            dedent(
                f"""
                scene Demo
                pipeArc Elbow
                    at 10 20 30
                    pipeRadius 0.25
                    bendRadius 2
                    angle {angle}
                    segments 4
                    rotate {rotation}
                    color steelgray
                """
            ).strip()
        )
        return iter_render_objects(scene)

    def test_expands_to_cylinders_with_arc_lengths(self):
        objects = self._render()
        self.assertEqual(len(objects), 4)
        self.assertTrue(all(obj["type"] == "cylinder" for obj in objects))
        self.assertEqual(objects[0]["name"], "Elbow_segment_01")
        self.assertAlmostEqual(objects[0]["height"], 2 * 3.141592653589793 / 2 / 4)
        self.assertEqual(objects[0]["radius"], 0.25)

    def test_positive_and_negative_angles_bend_in_opposite_directions(self):
        positive = self._render(90)[0]["position"]
        negative = self._render(-90)[0]["position"]
        self.assertGreater(positive[0], 10)
        self.assertGreater(positive[1], 20)
        self.assertGreater(negative[0], 10)
        self.assertLess(negative[1], 20)

    def test_rotates_the_whole_arc(self):
        unrotated = self._render()[0]["position"]
        rotated = self._render(rotation="0 0 90")[0]["position"]
        self.assertAlmostEqual(rotated[0] - 10, -(unrotated[1] - 20))
        self.assertAlmostEqual(rotated[1] - 20, unrotated[0] - 10)

    def test_segment_orientation_composes_with_parent_rotation(self):
        objects = self._render(rotation="35 20 10")
        segment = objects[0]
        world_axis = _apply_rotation(segment["rotation"], [0.0, 1.0, 0.0])

        local_midpoint_angle = math.radians(90 / 4 * 0.5)
        local_tangent = [math.cos(local_midpoint_angle), math.sin(local_midpoint_angle), 0.0]
        expected_axis = _apply_matrix(_rotation_matrix([35, 20, 10]), local_tangent)

        self.assertAlmostEqual(world_axis[0], expected_axis[0], places=6)
        self.assertAlmostEqual(world_axis[1], expected_axis[1], places=6)
        self.assertAlmostEqual(world_axis[2], expected_axis[2], places=6)

    def test_segment_orientation_composes_at_xyz_gimbal_lock(self):
        objects = self._render(rotation="90 90 0")
        parent_rotation = _rotation_matrix([90, 90, 0])

        for index, segment in enumerate(objects):
            with self.subTest(segment=index):
                world_axis = _apply_rotation(segment["rotation"], [0.0, 1.0, 0.0])
                midpoint_angle = math.radians(90 / 4 * (index + 0.5))
                local_tangent = [math.cos(midpoint_angle), math.sin(midpoint_angle), 0.0]
                expected_axis = _apply_matrix(parent_rotation, local_tangent)

                self.assertAlmostEqual(world_axis[0], expected_axis[0], places=6)
                self.assertAlmostEqual(world_axis[1], expected_axis[1], places=6)
                self.assertAlmostEqual(world_axis[2], expected_axis[2], places=6)

    def test_can_be_used_inside_a_component(self):
        scene = parse_text(
            dedent(
                """
                scene Demo
                component Pipe
                    param pipeBend 3
                    pipeArc Bend
                        at 1 0 0
                        pipeRadius 0.2
                        bendRadius pipeBend
                        angle 90
                        segments 2
                        color gray
                instance Pipe01 Pipe
                    at 10 0 0
                    rotate 0 90 0
                """
            ).strip()
        )
        objects = iter_render_objects(scene)
        self.assertEqual(len(objects), 2)
        self.assertEqual(objects[0]["name"], "Pipe01.Bend_segment_01")

    def test_rejects_invalid_properties(self):
        valid_properties = {
            "pipeRadius": "1",
            "bendRadius": "2",
            "angle": "90",
            "segments": "4",
        }
        for property_name in valid_properties:
            properties = {**valid_properties, property_name: "0"}
            source = dedent(
                f"""
                scene Demo
                pipeArc Invalid
                    at 0 0 0
                    pipeRadius {properties['pipeRadius']}
                    bendRadius {properties['bendRadius']}
                    angle {properties['angle']}
                    segments {properties['segments']}
                    color gray
                """
            ).strip()
            with self.subTest(property_name=property_name):
                with self.assertRaises(SGSLValidationError):
                    parse_text(source)


def _rotation_matrix(rotation):
    rx, ry, rz = (math.radians(value) for value in rotation)
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    cos_z, sin_z = math.cos(rz), math.sin(rz)
    return [
        [cos_y * cos_z, -cos_y * sin_z, sin_y],
        [sin_x * sin_y * cos_z + cos_x * sin_z, -sin_x * sin_y * sin_z + cos_x * cos_z, -sin_x * cos_y],
        [-cos_x * sin_y * cos_z + sin_x * sin_z, cos_x * sin_y * sin_z + sin_x * cos_z, cos_x * cos_y],
    ]


def _apply_matrix(matrix, vector):
    return [
        sum(matrix[0][index] * vector[index] for index in range(3)),
        sum(matrix[1][index] * vector[index] for index in range(3)),
        sum(matrix[2][index] * vector[index] for index in range(3)),
    ]


def _apply_rotation(rotation, vector):
    return _apply_matrix(_rotation_matrix(rotation), vector)


if __name__ == "__main__":
    unittest.main()
