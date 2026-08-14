from __future__ import annotations

import json
from pathlib import Path

from sgsl.colors import resolve_color
from sgsl.primitives import iter_render_objects
from sgsl.frustum_geometry import frustum_geometry
from sgsl.hollow_frustum_geometry import hollow_frustum_geometry
from sgsl.hollow_pipe_arc_geometry import hollow_pipe_arc_geometry
from sgsl.pipe_arc_geometry import pipe_arc_geometry
from sgsl.profile_revolve_geometry import profile_revolve_geometry
from sgsl.spherical_cap_geometry import spherical_cap_geometry
from sgsl.sphere_geometry import sphere_geometry


def render(scene: dict) -> dict:
    return {
        "scene": scene["scene"],
        "objects": [
            _render_object(obj)
            for obj in iter_render_objects(
                scene,
                expand_pipe_arcs=False,
                expand_frustums=False,
                expand_spherical_caps=False,
                include_runtime_assets=True,
            )
            if obj["type"] != "runtime_asset_instance" or "bounds" in obj
        ],
    }


def _render_object(obj: dict) -> dict:
    if obj["type"] == "runtime_asset_instance":
        payload = {
            "type": "runtime_asset",
            "name": obj["name"],
            "asset": obj["asset"],
            "position": obj["position"],
            "rotation": obj["rotation"],
            "scale": obj["scale"],
            "bounds": obj.get("bounds", [2.0, 2.0, 2.0]),
            "robloxName": obj.get("roblox_name", obj["asset"]),
        }
        if "asset_symbol" in obj:
            payload["assetSymbol"] = obj["asset_symbol"]
        if "roblox_id" in obj:
            payload["robloxId"] = obj["roblox_id"]
        return payload
    if obj["type"] == "marker":
        return {
            "type": "marker",
            "name": obj["name"],
            "position": obj["position"],
            "rotation": obj["rotation"],
        }
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
    elif obj["type"] == "frustum":
        payload["vertices"], payload["indices"] = frustum_geometry(
            obj["radius_bottom"], obj["radius_top"], obj["height"], obj["segments"]
        )
    elif obj["type"] == "spherical_cap":
        payload["vertices"], payload["indices"] = spherical_cap_geometry(
            obj["base_radius"], obj["height"], obj["segments"]
        )
    elif obj["type"] == "sphere":
        payload["vertices"], payload["indices"] = sphere_geometry(obj["radius"], obj["segments"])
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
    elif obj["type"] == "profile_revolve":
        payload["vertices"], payload["indices"] = profile_revolve_geometry(
            obj["profile"], obj["segments"], obj.get("thickness")
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
