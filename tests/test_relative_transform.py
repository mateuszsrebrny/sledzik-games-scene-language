import math
import unittest

from sgsl.primitives import (
    _make_transform,
    _multiply_transforms,
    invert_transform,
    relative_transform,
)


def _assert_transforms_close(test, left, right, places=6):
    for row in range(4):
        for column in range(4):
            test.assertAlmostEqual(left[row][column], right[row][column], places=places)


class InvertTransformTests(unittest.TestCase):
    def test_round_trip_is_identity(self):
        transform = _make_transform([3.0, -1.5, 7.0], [15.0, -40.0, 90.0])
        identity = _multiply_transforms(invert_transform(transform), transform)
        _assert_transforms_close(self, identity, _make_transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))

    def test_identity_transform_inverts_to_itself(self):
        transform = _make_transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
        _assert_transforms_close(self, invert_transform(transform), transform)


class RelativeTransformTests(unittest.TestCase):
    def test_anchor_times_offset_reconstructs_target(self):
        anchor_position = [-0.66825, 1.0125, 2.6325]
        anchor_rotation = [0.0, 0.0, 0.0]
        target_position = [8.0055, 0.0675, 2.6325]
        target_rotation = [12.0, -33.0, 5.0]

        offset = relative_transform(anchor_position, anchor_rotation, target_position, target_rotation)
        anchor_transform = _make_transform(anchor_position, anchor_rotation)
        reconstructed = _multiply_transforms(anchor_transform, offset)

        _assert_transforms_close(
            self, reconstructed, _make_transform(target_position, target_rotation)
        )

    def test_identity_anchor_offset_equals_target(self):
        # bottle.sgsl's actual case: Shell has no authored rotation, so the
        # Grip marker's offset from it should just be the marker's own
        # authored transform, unchanged.
        target_position = [0.74, 1.15785, 0.0]
        target_rotation = [0.0, 0.0, 90.0]

        offset = relative_transform([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], target_position, target_rotation)
        _assert_transforms_close(self, offset, _make_transform(target_position, target_rotation))

    def test_rotated_anchor_removes_its_own_rotation_from_the_offset(self):
        # A marker sitting exactly on a 90-degree-Z-rotated anchor's own
        # origin, with no rotation of its own, must produce an offset that
        # undoes the anchor's rotation - since anchor.CFrame * offset must
        # reconstruct the marker's un-rotated world transform.
        anchor_position = [1.0, 2.0, 3.0]
        anchor_rotation = [0.0, 0.0, 90.0]
        target_position = anchor_position
        target_rotation = [0.0, 0.0, 0.0]

        offset = relative_transform(anchor_position, anchor_rotation, target_position, target_rotation)
        offset_rotation_z = math.degrees(math.atan2(offset[1][0], offset[0][0]))
        self.assertAlmostEqual(offset_rotation_z, -90.0, places=6)
        for row in range(3):
            self.assertAlmostEqual(offset[row][3], 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
