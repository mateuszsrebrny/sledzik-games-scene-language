import unittest

from sgsl.colors import color_to_rgb, resolve_color


class ColorTests(unittest.TestCase):
    def test_resolves_common_named_colors(self):
        cases = {
            "white": "#ffffff",
            "gray": "#808080",
            "lightgray": "#d2d2d2",
            "darkgray": "#5a5a5a",
            "steelgray": "#8a949e",
            "lightblue": "#b7ddff",
            "orange": "#ff9800",
            "green": "#4caf50",
            "navy": "#000080",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(resolve_color(name), expected)

    def test_resolves_hex_and_is_case_insensitive(self):
        self.assertEqual(resolve_color("#B7DDFF"), "#b7ddff")
        self.assertEqual(resolve_color("LightBlue"), "#b7ddff")

    def test_converts_to_rgb(self):
        self.assertEqual(color_to_rgb("lightblue"), (183, 221, 255))


if __name__ == "__main__":
    unittest.main()
