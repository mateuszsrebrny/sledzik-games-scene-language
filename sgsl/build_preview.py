from __future__ import annotations

from pathlib import Path

from sgsl.parser import parse_file
from sgsl.renderers.html_renderer import write


def build_preview(source_path: str | Path, output_path: str | Path = "preview/scene.json") -> Path:
    scene = parse_file(source_path)
    return write(scene, output_path)
