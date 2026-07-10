from __future__ import annotations

import math


def iter_render_objects(scene: dict) -> list[dict]:
    objects: list[dict] = []
    for obj in scene["objects"]:
        if obj["type"] == "frustum":
            objects.extend(_expand_frustum(obj))
        elif obj["type"] == "ring":
            objects.extend(_expand_ring(obj))
        else:
            objects.append(obj)
    return objects


def _expand_frustum(obj: dict) -> list[dict]:
    segments = obj["segments"]
    segment_height = obj["height"] / segments
    center_x, center_y, center_z = obj["position"]
    bottom_y = center_y - obj["height"] / 2

    expanded: list[dict] = []
    for index in range(segments):
        t = (index + 0.5) / segments
        radius = _lerp(obj["radius_bottom"], obj["radius_top"], t)
        segment_center_y = bottom_y + segment_height * (index + 0.5)
        expanded.append(
            {
                "type": "cylinder",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": [center_x, segment_center_y, center_z],
                "radius": radius,
                "height": segment_height,
                "color": obj["color"],
                "transparency": obj["transparency"],
            }
        )

    return expanded


def _lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def _expand_ring(obj: dict) -> list[dict]:
    segments = obj["segments"]
    outer_radius = obj["radius_outer"]
    inner_radius = obj["radius_inner"]
    mid_radius = (outer_radius + inner_radius) / 2
    thickness = outer_radius - inner_radius
    segment_span = (2 * math.pi * mid_radius) / segments
    segment_size = max(thickness, segment_span * 0.9)
    center_x, center_y, center_z = obj["position"]

    expanded: list[dict] = []
    for index in range(segments):
        angle = (2 * math.pi * index) / segments
        offset_x = math.cos(angle) * mid_radius
        offset_z = math.sin(angle) * mid_radius
        expanded.append(
            {
                "type": "block",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": [center_x + offset_x, center_y, center_z + offset_z],
                "size": [segment_size, obj["height"], segment_size],
                "color": obj["color"],
                "transparency": obj["transparency"],
            }
        )

    return expanded
