from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sgsl.parser import SGSLValidationError, parse_text
from sgsl.renderers.html_renderer import render as render_html


ROOT = Path(__file__).resolve().parent
DEFAULT_HOST = os.environ.get("SGSL_PREVIEW_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("SGSL_PREVIEW_PORT", "8000"))


def build_preview_payload(source: str) -> dict[str, Any]:
    scene = parse_text(source)
    return render_html(scene)


class PreviewRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
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
            payload = build_preview_payload(source)
        except SGSLValidationError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except ValueError as exc:
            self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), PreviewRequestHandler)
    print(f"Serving SGSL preview on http://{args.host}:{args.port}/preview/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
