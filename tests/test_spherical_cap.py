import unittest
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.primitives import iter_render_objects
from sgsl.renderers.roblox_renderer import render as render_roblox


class SphericalCapTests(unittest.TestCase):
    def _scene(self, segments=6, base_radius=1.6, height=0.65, rotation="0 0 0"):
        return parse_text(
            dedent(
                f"""
                scene Demo
                sphericalCap Dome
                    at 0 0 0
                    baseRadius {base_radius}
                    height {height}
                    segments {segments}
                    rotate {rotation}
                    color gray
                """
            ).strip()
        )

    def test_expands_into_smaller_segments_towards_the_top(self):
        objects = iter_render_objects(self._scene())
        self.assertEqual(len(objects), 6)
        self.assertTrue(all(obj["type"] == "cylinder" for obj in objects))
        self.assertGreater(objects[0]["radius"], objects[-1]["radius"])
        self.assertLess(objects[0]["position"][1], objects[-1]["position"][1])

    def test_rotates_with_the_cap(self):
        unrotated = iter_render_objects(self._scene())[0]["position"]
        rotated = iter_render_objects(self._scene(rotation="0 0 90"))[0]["position"]
        self.assertAlmostEqual(rotated[0], -unrotated[1], places=6)
        self.assertAlmostEqual(rotated[1], unrotated[0], places=6)

    def test_is_rendered_by_the_roblox_backend(self):
        source = render_roblox(self._scene())
        self.assertIn("makeSteppedFrustum", source)
        self.assertNotIn("Unsupported render object type", source)

    def test_rejects_missing_or_invalid_properties(self):
        for source in (
            """
            scene Demo
            sphericalCap Invalid
                at 0 0 0
                height 1
                segments 4
                color gray
            """,
            """
            scene Demo
            sphericalCap Invalid
                at 0 0 0
                baseRadius 1
                height 1
                segments 0
                color gray
            """,
        ):
            with self.subTest(source=source):
                with self.assertRaises(SGSLValidationError):
                    parse_text(dedent(source).strip())


if __name__ == "__main__":
    unittest.main()
