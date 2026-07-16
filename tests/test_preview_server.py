import unittest
import tempfile
from pathlib import Path
from textwrap import dedent

from preview_server import build_preview_payload, resolve_library_paths
from sgsl.parser import SGSLValidationError


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

    def test_builds_preview_with_an_allowed_import(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            library = root / "components" / "marker.sgsl"
            library.parent.mkdir()
            library.write_text(
                dedent(
                    """
                    component Marker
                        block Dot
                            at 0 0 0
                            size 1 1 1
                            color red
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            payload = build_preview_payload(
                'scene Demo\nimport "marker.sgsl"\ninstance Here Marker',
                (library,),
                base_dir=root,
            )

        self.assertEqual(payload["objects"][0]["name"], "Here.Dot")

    def test_rejects_imports_outside_the_allowed_library(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            hidden = root / "hidden.sgsl"
            hidden.write_text("component Hidden\n", encoding="utf-8")

            with self.assertRaisesRegex(SGSLValidationError, "not available in the preview library"):
                build_preview_payload(
                    'scene Demo\nimport "hidden.sgsl"',
                    (root / "allowed.sgsl",),
                    base_dir=root,
                )

    def test_import_error_explains_how_to_add_a_library(self):
        with self.assertRaisesRegex(SGSLValidationError, "Add the file with --library"):
            build_preview_payload('scene Demo\nimport "missing.sgsl"')

    def test_allows_transitive_imports_when_every_file_is_listed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            frame = root / "components" / "frame.sgsl"
            window = root / "components" / "window.sgsl"
            frame.parent.mkdir()
            frame.write_text(
                "component Frame\n    block Bar\n        at 0 0 0\n        size 1 1 1\n        color gray\n",
                encoding="utf-8",
            )
            window.write_text(
                'import "frame.sgsl"\ncomponent Window\n    instance Border Frame\n',
                encoding="utf-8",
            )

            payload = build_preview_payload(
                'scene Demo\nimport "window.sgsl"\ninstance Main Window',
                (window, frame),
                base_dir=root,
            )

        self.assertEqual(payload["objects"][0]["name"], "Main.Border.Bar")

    def test_requires_a_path_for_ambiguous_library_filenames(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            left = root / "left" / "shared.sgsl"
            right = root / "right" / "shared.sgsl"
            left.parent.mkdir()
            right.parent.mkdir()
            left.write_text("component Left\n", encoding="utf-8")
            right.write_text("component Right\n", encoding="utf-8")

            with self.assertRaisesRegex(SGSLValidationError, "matches multiple"):
                build_preview_payload(
                    'scene Demo\nimport "shared.sgsl"',
                    (left, right),
                    base_dir=root,
                )

    def test_resolves_globbed_library_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            one = root / "one.sgsl"
            two = root / "two.sgsl"
            one.write_text("component One\n", encoding="utf-8")
            two.write_text("component Two\n", encoding="utf-8")

            paths = resolve_library_paths([str(root / "*.sgsl")])

        self.assertEqual(set(paths), {one.resolve(), two.resolve()})


if __name__ == "__main__":
    unittest.main()
