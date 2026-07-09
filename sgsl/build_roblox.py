from __future__ import annotations

from pathlib import Path

from sgsl.parser import parse_file
from sgsl.renderers.roblox_renderer import write


def build_roblox(source_path: str | Path, output_path: str | Path | None = None) -> Path:
    source = Path(source_path)
    if output_path is None:
        output_path = Path("build") / f"{source.stem}.lua"
    scene = parse_file(source)
    return write(scene, output_path)
