import tempfile
import unittest
from pathlib import Path

from sgsl.parser import SGSLValidationError, parse_file, parse_text


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write(self, relative_path: str, source: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source.strip() + "\n", encoding="utf-8")
        return path

    def test_loads_relative_and_transitive_imports(self):
        self._write(
            "components/frame.sgsl",
            """
component Frame
    block Bar
        at 1 0 0
        size 2 1 1
        color gray
            """,
        )
        self._write(
            "components/window.sgsl",
            """
import "frame.sgsl"
component Window
    instance WindowFrame Frame
        at 2 0 0
            """,
        )
        entry = self._write(
            "scenes/demo.sgsl",
            """
scene Demo
import "../components/window.sgsl"
instance MainWindow Window
    at 10 0 0
            """,
        )

        scene = parse_file(entry)

        self.assertEqual(scene["objects"][0]["name"], "MainWindow.WindowFrame.Bar")
        self.assertEqual(scene["objects"][0]["position"], [13.0, 0.0, 0.0])

    def test_skips_the_same_resolved_file_imported_more_than_once(self):
        self._write(
            "component.sgsl",
            """
component Marker
    block Part
        at 0 0 0
        size 1 1 1
        color red
            """,
        )
        entry = self._write(
            "demo.sgsl",
            """
scene Demo
import "component.sgsl"
import "./component.sgsl"
instance Marker01 Marker
            """,
        )

        self.assertEqual(len(parse_file(entry)["objects"]), 1)

    def test_reports_import_cycles(self):
        entry = self._write("a.sgsl", 'scene Demo\nimport "b.sgsl"')
        self._write("b.sgsl", 'import "a.sgsl"')

        with self.assertRaisesRegex(SGSLValidationError, r"a\.sgsl -> b\.sgsl -> a\.sgsl"):
            parse_file(entry)

    def test_reports_missing_import_with_importer(self):
        entry = self._write("demo.sgsl", 'scene Demo\nimport "missing.sgsl"')

        with self.assertRaisesRegex(SGSLValidationError, r"(?s)Could not import 'missing\.sgsl'.*demo\.sgsl"):
            parse_file(entry)

    def test_reports_duplicate_components_with_both_files(self):
        self._write("one.sgsl", "component Shared")
        self._write("two.sgsl", "component Shared")
        entry = self._write(
            "demo.sgsl",
            'scene Demo\nimport "one.sgsl"\nimport "two.sgsl"',
        )

        with self.assertRaisesRegex(SGSLValidationError, r"(?s)Component 'Shared'.*one\.sgsl.*two\.sgsl"):
            parse_file(entry)

    def test_parse_text_rejects_imports_without_a_base_path(self):
        with self.assertRaisesRegex(SGSLValidationError, "Imports require a source file"):
            parse_text('scene Demo\nimport "component.sgsl"')


if __name__ == "__main__":
    unittest.main()
