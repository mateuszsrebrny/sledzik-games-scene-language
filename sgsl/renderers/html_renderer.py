from __future__ import annotations

import json
from pathlib import Path

from sgsl.colors import resolve_color
from sgsl.primitives import iter_render_objects
from sgsl.hollow_frustum_geometry import hollow_frustum_geometry
from sgsl.hollow_pipe_arc_geometry import hollow_pipe_arc_geometry
from sgsl.pipe_arc_geometry import pipe_arc_geometry


def render(scene: dict) -> dict:
    return {
        "scene": scene["scene"],
        "objects": [_render_object(obj) for obj in iter_render_objects(scene, expand_pipe_arcs=False)],
    }


def _render_object(obj: dict) -> dict:
    payload = {
        "type": obj["type"],
        "name": obj["name"],
        "position": obj["position"],
        "rotation": obj["rotation"],
        "color": resolve_color(obj["color"]),
        "transparency": obj["transparency"],
        "emissive": obj["emissive"],
        "material": obj["material"],
    }
    if obj["type"] in ("block", "wedge"):
        payload["size"] = obj["size"]
    elif obj["type"] == "cylinder":
        payload["radius"] = obj["radius"]
        payload["height"] = obj["height"]
    elif obj["type"] == "hollow_frustum":
        payload["vertices"], payload["indices"] = hollow_frustum_geometry(
            obj["outer_bottom_radius"], obj["outer_top_radius"],
            obj["inner_bottom_radius"], obj["inner_top_radius"],
            obj["height"], obj["segments"],
            obj["start_angle"], obj["angle"],
        )
    elif obj["type"] == "hollow_pipe_arc":
        payload["vertices"], payload["indices"] = hollow_pipe_arc_geometry(
            obj["outer_radius"], obj["inner_radius"], obj["bend_radius"],
            obj["angle"], obj["segments"], obj["start_angle"],
            obj["cross_start_angle"], obj["cross_angle"],
        )
    elif obj["type"] == "pipe_arc":
        payload["vertices"], payload["indices"] = pipe_arc_geometry(
            obj["pipe_radius"], obj["bend_radius"], obj["angle"], obj["segments"]
        )
    else:
        raise ValueError(f"Unsupported render object type: {obj['type']}")
    return payload


def write(scene: dict, output_path: str | Path) -> Path:
    payload = render(scene)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
