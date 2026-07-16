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
from urllib.parse import urlparse

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
        **kwargs: Any,
    ) -> None:
        self.library_paths = library_paths
        self.library_base_dir = library_base_dir
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/preview":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")

        try:
            source = self._extract_source(raw_body, content_type)
            payload = build_preview_payload(
                source,
                self.library_paths,
                base_dir=self.library_base_dir,
            )
        except SGSLValidationError as exc:
            traceback.print_exc()
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except ValueError as exc:
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

    def _extract_source(self, raw_body: str, content_type: str) -> str:
        if "application/json" in content_type:
            data = json.loads(raw_body or "{}")
            source = data.get("source", "")
            if not isinstance(source, str):
                raise ValueError("Request body field 'source' must be a string.")
            return source
        return raw_body

    def _write_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
        "--library",
        nargs="+",
        action="extend",
        default=[],
        metavar="FILE",
        help="SGSL files allowed as imports in live editor source; shell and quoted glob patterns are supported",
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


def main() -> int:
    args = parse_args()
    try:
        library_paths = resolve_library_paths(args.library)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    library_base_dir = Path.cwd().resolve()
    handler = partial(
        PreviewRequestHandler,
        library_paths=library_paths,
        library_base_dir=library_base_dir,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving SGSL preview on http://{args.host}:{args.port}/preview/")
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
