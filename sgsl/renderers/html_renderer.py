from __future__ import annotations

import json
from pathlib import Path

from sgsl.colors import resolve_color


def render(scene: dict) -> dict:
    return {
        "scene": scene["scene"],
        "objects": [
            {
                "type": obj["type"],
                "name": obj["name"],
                "position": obj["position"],
                "size": obj["size"],
                "color": resolve_color(obj["color"]),
                "transparency": obj["transparency"],
            }
            for obj in scene["objects"]
        ],
    }


def write(scene: dict, output_path: str | Path) -> Path:
    payload = render(scene)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
