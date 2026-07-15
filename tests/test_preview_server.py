import unittest
from textwrap import dedent

from preview_server import build_preview_payload


class PreviewServerTests(unittest.TestCase):
    def test_builds_preview_payload_from_sgsl_text(self):
        payload = build_preview_payload(
            dedent(
                """
                scene Demo

                block Floor
                    at 0 -0.15 0
                    size 16 0.3 10
                    color lightgray
                """
            ).strip()
        )

        self.assertEqual(payload["scene"], "Demo")
        self.assertEqual(len(payload["objects"]), 1)
        self.assertEqual(payload["objects"][0]["name"], "Floor")
        self.assertEqual(payload["objects"][0]["color"], "#d2d2d2")


if __name__ == "__main__":
    unittest.main()
