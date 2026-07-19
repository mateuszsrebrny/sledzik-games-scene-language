import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.renderers.glb_renderer import write
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


class WedgeTests(unittest.TestCase):
    SOURCE = dedent(
        """
        scene Demo
        wedge Roof
            at 1 2 3
            size 4 2 6
            rotate 0 90 0
            color red
        """
    ).strip()

    def test_parses_and_reaches_preview(self):
        payload = render_html(parse_text(self.SOURCE))["objects"][0]
        self.assertEqual(payload["type"], "wedge")
        self.assertEqual(payload["size"], [4.0, 2.0, 6.0])
        self.assertEqual(payload["rotation"], [0.0, 90.0, 0.0])

    def test_roblox_uses_native_wedge_part_builder(self):
        source = render_roblox(parse_text(self.SOURCE))
        self.assertIn("Builder.makeWedge", source)
        self.assertIn("Vector3.new(4.0, 2.0, 6.0)", source)

    def test_glb_renderer_accepts_wedge(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write(parse_text(self.SOURCE), Path(directory) / "wedge.glb")
            self.assertGreater(path.stat().st_size, 0)

    def test_rejects_invalid_size(self):
        with self.assertRaises(SGSLValidationError):
            parse_text(self.SOURCE.replace("size 4 2 6", "size 4 0 6"))


if __name__ == "__main__":
    unittest.main()
