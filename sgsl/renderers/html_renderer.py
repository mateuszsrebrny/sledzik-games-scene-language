from __future__ import annotations

import json
from pathlib import Path

from sgsl.colors import resolve_color
from sgsl.primitives import iter_render_objects


def render(scene: dict) -> dict:
    return {
        "scene": scene["scene"],
        "objects": [_render_object(obj) for obj in iter_render_objects(scene)],
    }


def _render_object(obj: dict) -> dict:
    payload = {
        "type": obj["type"],
        "name": obj["name"],
        "position": obj["position"],
        "rotation": obj["rotation"],
        "color": resolve_color(obj["color"]),
        "transparency": obj["transparency"],
    }
    if obj["type"] == "block":
        payload["size"] = obj["size"]
    elif obj["type"] == "cylinder":
        payload["radius"] = obj["radius"]
        payload["height"] = obj["height"]
    else:
        raise ValueError(f"Unsupported render object type: {obj['type']}")
    return payload


def write(scene: dict, output_path: str | Path) -> Path:
    payload = render(scene)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
