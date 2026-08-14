from __future__ import annotations

import json
from pathlib import Path


def manifest(scene: dict) -> dict:
    entries = []
    for obj in scene.get("objects", []):
        if obj.get("type") != "runtime_asset_instance":
            continue
        entry = {
            "name": obj["name"],
            "asset": obj["asset"],
            "position": obj["position"],
            "rotation": obj["rotation"],
            "scale": obj["scale"],
        }
        for source_key, manifest_key in (
            ("asset_symbol", "assetSymbol"),
            ("roblox_name", "robloxName"),
            ("roblox_id", "robloxId"),
            ("bounds", "bounds"),
        ):
            if source_key in obj:
                entry[manifest_key] = obj[source_key]
        entries.append(entry)
    return {"version": 1, "scene": scene["scene"], "runtimeAssets": entries}


def write_manifest(scene: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest(scene), indent=2) + "\n", encoding="utf-8")
    return path
