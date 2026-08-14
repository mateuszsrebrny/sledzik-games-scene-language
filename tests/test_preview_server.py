import unittest
import tempfile
from pathlib import Path
from textwrap import dedent

from preview_server import (
    build_preview_payload,
    component_preview_source,
    find_entry_component_names,
    list_scene_paths,
    load_default_source,
    prepare_selected_source,
    resolve_library_paths,
    resolve_scene_path,
    resolve_scene_root,
    select_preview_components,
)
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

    def test_wraps_component_only_source_with_a_preview_scene(self):
        source = "component Marker\n    block Dot\n        size 1 1 1\n"
        wrapped = component_preview_source(source, ("Marker",), "Preview_marker")

        self.assertTrue(wrapped.startswith("scene Preview_marker\n"))
        self.assertIn("instance Preview1 Marker", wrapped)

    def test_selects_file_named_public_component_over_helper_components(self):
        self.assertEqual(
            select_preview_components(
                Path("factory-hall.sgsl"),
                ("WallFragment", "FactoryWindow", "FactoryHall"),
            ),
            ("FactoryHall",),
        )

    def test_selects_last_component_when_filename_has_no_exact_match(self):
        self.assertEqual(
            select_preview_components(
                Path("asset.sgsl"),
                ("Helper", "PublicAsset"),
            ),
            ("PublicAsset",),
        )

    def test_finds_only_components_declared_by_selected_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            imported = root / "shared.sgsl"
            selected = root / "selected.sgsl"
            imported.write_text("component Shared\n", encoding="utf-8")
            selected.write_text(
                'import "shared.sgsl"\ncomponent Selected\n',
                encoding="utf-8",
            )

            self.assertEqual(find_entry_component_names(selected), ("Selected",))

    def test_prepares_component_file_for_preview_without_editing_it(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            selected = Path(temporary_directory) / "house.sgsl"
            original = "component House\n    block Wall\n        size 2 2 2\n"
            selected.write_text(original, encoding="utf-8")

            prepared = prepare_selected_source(selected.read_text(encoding="utf-8"), selected)

            self.assertIn("scene Preview_house", prepared)
            self.assertIn("instance Preview1 House", prepared)
            self.assertEqual(selected.read_text(encoding="utf-8"), original)

    def test_component_preview_resolves_imports_from_selected_file_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            helper = root / "helper.sgsl"
            selected = root / "selected.sgsl"
            helper.write_text(
                "component Helper\n    block Dot\n        at 0 0 0\n        size 1 1 1\n        color gray\n",
                encoding="utf-8",
            )
            selected.write_text(
                'import "helper.sgsl"\ncomponent Selected\n    instance Part Helper\n',
                encoding="utf-8",
            )
            source = prepare_selected_source(selected.read_text(encoding="utf-8"), selected)

            payload = build_preview_payload(
                source,
                (helper, selected),
                base_dir=selected.parent,
            )

        self.assertEqual(payload["scene"], "Preview_selected")
        self.assertEqual([obj["name"] for obj in payload["objects"]], ["Preview1.Part.Dot"])

    def test_keeps_existing_scene_source_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            selected = Path(temporary_directory) / "preview.sgsl"
            original = "scene Existing\n"
            selected.write_text(original, encoding="utf-8")

            self.assertEqual(prepare_selected_source(original, selected), original)

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

    def test_loads_configured_default_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "preview.sgsl"
            source.write_text("scene Default\n", encoding="utf-8")

            loaded = load_default_source(str(source))

        self.assertEqual(loaded, "scene Default\n")

    def test_rejects_missing_default_source(self):
        with self.assertRaisesRegex(ValueError, "Default preview source is not a file"):
            load_default_source("missing-preview.sgsl")

    def test_lists_sgsl_files_recursively_with_normalized_relative_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "components" / "city").mkdir(parents=True)
            (root / "preview.sgsl").write_text("scene Preview\n", encoding="utf-8")
            (root / "components" / "city" / "house.sgsl").write_text("component House\n", encoding="utf-8")
            (root / "ignored.txt").write_text("ignored\n", encoding="utf-8")

            scenes = list_scene_paths(root)

        self.assertEqual(scenes, ["components/city/house.sgsl", "preview.sgsl"])

    def test_resolves_scene_inside_configured_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            scene = root / "components" / "house.sgsl"
            scene.parent.mkdir()
            scene.write_text("component House\n", encoding="utf-8")

            resolved = resolve_scene_path(root, "components/house.sgsl")

        self.assertEqual(resolved, scene.resolve())

    def test_rejects_scene_path_escaping_configured_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            parent = Path(temporary_directory)
            root = parent / "root"
            root.mkdir()
            (parent / "outside.sgsl").write_text("scene Outside\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_scene_path(root, "../outside.sgsl")

    def test_rejects_non_sgsl_scene(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "notes.txt").write_text("not a scene\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "SGSL scene file was not found"):
                resolve_scene_path(root, "notes.txt")

    def test_uses_default_source_directory_as_implicit_scene_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "preview.sgsl"
            source.write_text("scene Preview\n", encoding="utf-8")

            resolved = resolve_scene_root(None, str(source))

        self.assertEqual(resolved, root.resolve())


if __name__ == "__main__":
    unittest.main()
