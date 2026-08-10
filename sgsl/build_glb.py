from __future__ import annotations

from pathlib import Path

from sgsl.parser import parse_component_file
from sgsl.renderers.glb_renderer import write


def build_glb(
    source_path: str | Path,
    component: str,
    output_path: str | Path | None = None,
    *,
    merge_ungrouped_materials: bool = False,
) -> Path:
    source = Path(source_path)
    output = Path(output_path) if output_path else Path("build") / f"{component}.glb"
    return write(
        parse_component_file(source, component),
        output,
        merge_ungrouped_materials=merge_ungrouped_materials,
    )
