from __future__ import annotations

import argparse
import glob
import json
import os
import traceback
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from sgsl.parser import SGSLValidationError, parse_text_with_library
from sgsl.renderers.html_renderer import render as render_html


ROOT = Path(__file__).resolve().parent
DEFAULT_HOST = os.environ.get("SGSL_PREVIEW_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("SGSL_PREVIEW_PORT", "8000"))


def build_preview_payload(
    source: str,
    library_paths: tuple[Path, ...] = (),
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    scene = parse_text_with_library(source, library_paths, base_dir=base_dir)
    return render_html(scene)


class PreviewRequestHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        library_paths: tuple[Path, ...] = (),
        library_base_dir: Path | None = None,
        scene_root: Path | None = None,
        default_source: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.library_paths = library_paths
        self.library_base_dir = library_base_dir
        self.scene_root = scene_root
        self.default_source = default_source
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenes":
            if self.scene_root is None:
                self._write_json({"scenes": []})
                return
            self._write_json({"scenes": list_scene_paths(self.scene_root)})
            return
        if parsed.path == "/api/source":
            try:
                scene_path = self._selected_scene_path(parsed.query)
                self._write_text(scene_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path != "/api/default-source":
            super().do_GET()
            return
        if self.default_source is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._write_text(self.default_source)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/preview":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")

        try:
            source, selected_scene = self._extract_preview_request(raw_body, content_type)
            if selected_scene is not None:
                if self.scene_root is None:
                    raise ValueError("Scene browsing is not configured for this preview server.")
                source = resolve_scene_path(self.scene_root, selected_scene).read_text(encoding="utf-8")
            payload = build_preview_payload(
                source,
                self.library_paths,
                base_dir=self.library_base_dir,
            )
        except SGSLValidationError as exc:
            traceback.print_exc()
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except (OSError, ValueError) as exc:
            traceback.print_exc()
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            traceback.print_exc()
            self._write_json(
                {"error": f"{type(exc).__name__}: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._write_json(payload)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _extract_preview_request(self, raw_body: str, content_type: str) -> tuple[str, str | None]:
        if "application/json" in content_type:
            data = json.loads(raw_body or "{}")
            source = data.get("source", "")
            scene = data.get("scene")
            if not isinstance(source, str):
                raise ValueError("Request body field 'source' must be a string.")
            if scene is not None and not isinstance(scene, str):
                raise ValueError("Request body field 'scene' must be a string.")
            return source, scene
        return raw_body, None

    def _selected_scene_path(self, query: str) -> Path:
        if self.scene_root is None:
            raise ValueError("Scene browsing is not configured for this preview server.")
        values = parse_qs(query).get("scene", [])
        if len(values) != 1:
            raise ValueError("Query parameter 'scene' is required exactly once.")
        return resolve_scene_path(self.scene_root, values[0])

    def _write_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_text(self, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SGSL live preview server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind (default: {DEFAULT_PORT})")
    parser.add_argument(
        "--root",
        metavar="DIRECTORY",
        help="Root directory exposed by the SGSL preview file browser",
    )
    parser.add_argument(
        "--library",
        nargs="+",
        action="extend",
        default=[],
        metavar="FILE",
        help="SGSL files allowed as imports in live editor source; shell and quoted glob patterns are supported",
    )
    parser.add_argument(
        "--default-source",
        metavar="FILE",
        help="SGSL file loaded into the live editor on startup and by the Load example button",
    )
    return parser.parse_args()


def resolve_library_paths(patterns: list[str]) -> tuple[Path, ...]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            raise ValueError(f"Preview library pattern matched no files: {pattern}")
        for match in sorted(matches):
            path = Path(match).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"Preview library path is not a file: {match}")
            if path not in seen:
                seen.add(path)
                resolved.append(path)
    return tuple(resolved)


def load_default_source(path: str | None) -> str | None:
    if path is None:
        return None
    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Default preview source is not a file: {path}")
    return source_path.read_text(encoding="utf-8")


def resolve_scene_root(path: str | None, default_source: str | None) -> Path | None:
    candidate = path
    if candidate is None and default_source is not None:
        candidate = str(Path(default_source).expanduser().resolve().parent)
    if candidate is None:
        return None
    root = Path(candidate).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Preview scene root is not a directory: {candidate}")
    return root


def list_scene_paths(scene_root: Path) -> list[str]:
    return sorted(
        path.relative_to(scene_root).as_posix()
        for path in scene_root.rglob("*.sgsl")
        if path.is_file()
    )


def resolve_scene_path(scene_root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise ValueError("Scene path must be a non-empty relative path.")
    root = scene_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Scene path escapes the configured SGSL root.") from exc
    if candidate.suffix.lower() != ".sgsl" or not candidate.is_file():
        raise ValueError(f"SGSL scene file was not found: {relative_path}")
    return candidate


def main() -> int:
    args = parse_args()
    try:
        library_paths = resolve_library_paths(args.library)
        default_source = load_default_source(args.default_source)
        scene_root = resolve_scene_root(args.root, args.default_source)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    library_base_dir = Path.cwd().resolve()
    handler = partial(
        PreviewRequestHandler,
        library_paths=library_paths,
        library_base_dir=library_base_dir,
        scene_root=scene_root,
        default_source=default_source,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving SGSL preview on http://{args.host}:{args.port}/preview/")
    if scene_root is not None:
        print(f"Preview scene root: {scene_root}")
    if library_paths:
        print("Preview import library:")
        for path in library_paths:
            print(f"  {path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
