from __future__ import annotations

import math
from collections import deque


def iter_render_objects(scene: dict) -> list[dict]:
    objects: list[dict] = []
    queue = deque(scene["objects"])

    while queue:
        obj = queue.popleft()
        if obj["type"] == "spherical_cap":
            queue.extend(_expand_spherical_cap(obj))
        elif obj["type"] == "frustum":
            queue.extend(_expand_frustum(obj))
        elif obj["type"] == "ring":
            queue.extend(_expand_ring(obj))
        elif obj["type"] == "pipe_arc":
            queue.extend(_expand_pipe_arc(obj))
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
        offset = _rotate_vector([0.0, segment_center_y - center_y, 0.0], obj["rotation"])
        expanded.append(
            {
                "type": "cylinder",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": [center_x + offset[0], center_y + offset[1], center_z + offset[2]],
                "radius": radius,
                "height": segment_height,
                "rotation": obj["rotation"],
                "color": obj["color"],
                "transparency": obj["transparency"],
                "emissive": obj["emissive"],
            }
        )

    return expanded


def _expand_spherical_cap(obj: dict) -> list[dict]:
    segments = obj["segments"]
    segment_height = obj["height"] / segments
    center_x, center_y, center_z = obj["position"]
    bottom_y = center_y - obj["height"] / 2
    sphere_radius = (obj["base_radius"] ** 2 + obj["height"] ** 2) / (2 * obj["height"])
    sphere_center_y = bottom_y + obj["height"] - sphere_radius

    expanded: list[dict] = []
    for index in range(segments):
        t0 = index / segments
        t1 = (index + 1) / segments
        y0 = bottom_y + obj["height"] * t0
        y1 = bottom_y + obj["height"] * t1
        radius_bottom = _spherical_cap_radius(y0, sphere_center_y, sphere_radius)
        radius_top = _spherical_cap_radius(y1, sphere_center_y, sphere_radius)
        segment_center_y = bottom_y + segment_height * (index + 0.5)
        offset = _rotate_vector([0.0, segment_center_y - center_y, 0.0], obj["rotation"])
        expanded.append(
            {
                "type": "frustum",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": [center_x + offset[0], center_y + offset[1], center_z + offset[2]],
                "radius_bottom": radius_bottom,
                "radius_top": radius_top,
                "height": segment_height,
                "segments": 1,
                "rotation": obj["rotation"],
                "color": obj["color"],
                "transparency": obj["transparency"],
                "emissive": obj["emissive"],
            }
        )

    return expanded


def _spherical_cap_radius(y: float, sphere_center_y: float, sphere_radius: float) -> float:
    offset = sphere_radius**2 - (y - sphere_center_y) ** 2
    return math.sqrt(max(0.0, offset))


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
        offset = _rotate_vector([offset_x, 0.0, offset_z], obj["rotation"])
        expanded.append(
            {
                "type": "block",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": [center_x + offset[0], center_y + offset[1], center_z + offset[2]],
                "size": [segment_size, obj["height"], segment_size],
                "rotation": obj["rotation"],
                "color": obj["color"],
                "transparency": obj["transparency"],
                "emissive": obj["emissive"],
            }
        )

    return expanded


def _expand_pipe_arc(obj: dict) -> list[dict]:
    segments = obj["segments"]
    total_angle = math.radians(obj["angle"])
    direction = 1.0 if total_angle > 0 else -1.0
    segment_angle = abs(total_angle) / segments
    segment_length = obj["bend_radius"] * abs(total_angle) / segments
    parent_transform = _make_transform(obj["position"], obj["rotation"])

    expanded: list[dict] = []
    for index in range(segments):
        midpoint_angle = segment_angle * (index + 0.5)
        local_position = [
            obj["bend_radius"] * math.sin(midpoint_angle),
            direction * obj["bend_radius"] * (1.0 - math.cos(midpoint_angle)),
            0.0,
        ]
        tangent_rotation = [0.0, 0.0, direction * midpoint_angle * 180.0 / math.pi - 90.0]
        local_transform = _make_transform(local_position, tangent_rotation)
        world_transform = _multiply_transforms(parent_transform, local_transform)
        expanded.append(
            {
                "type": "cylinder",
                "name": f"{obj['name']}_segment_{index + 1:02d}",
                "position": _transform_position(world_transform),
                "radius": obj["pipe_radius"],
                "height": segment_length,
                "rotation": _transform_rotation(world_transform),
                "color": obj["color"],
                "transparency": obj["transparency"],
                "emissive": obj["emissive"],
            }
        )

    return expanded


def _rotation_matrix(rotation: list[float]) -> list[list[float]]:
    rx, ry, rz = (math.radians(value) for value in rotation)
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    cos_z, sin_z = math.cos(rz), math.sin(rz)
    return [
        [cos_y * cos_z, -cos_y * sin_z, sin_y],
        [sin_x * sin_y * cos_z + cos_x * sin_z, -sin_x * sin_y * sin_z + cos_x * cos_z, -sin_x * cos_y],
        [-cos_x * sin_y * cos_z + sin_x * sin_z, cos_x * sin_y * sin_z + sin_x * cos_z, cos_x * cos_y],
    ]


def _make_transform(position: list[float], rotation: list[float]) -> list[list[float]]:
    rotation_matrix = _rotation_matrix(rotation)
    return [
        [rotation_matrix[0][0], rotation_matrix[0][1], rotation_matrix[0][2], position[0]],
        [rotation_matrix[1][0], rotation_matrix[1][1], rotation_matrix[1][2], position[1]],
        [rotation_matrix[2][0], rotation_matrix[2][1], rotation_matrix[2][2], position[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _multiply_transforms(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[row][index] * right[index][column] for index in range(4)) for column in range(4)]
        for row in range(4)
    ]


def _transform_position(transform: list[list[float]]) -> list[float]:
    return [transform[0][3], transform[1][3], transform[2][3]]


def _transform_rotation(transform: list[list[float]]) -> list[float]:
    rotation = [[transform[row][column] for column in range(3)] for row in range(3)]
    sin_y = max(-1.0, min(1.0, rotation[0][2]))
    y = math.asin(sin_y)
    if abs(math.cos(y)) > 1e-9:
        x = math.atan2(-rotation[1][2], rotation[2][2])
        z = math.atan2(-rotation[0][1], rotation[0][0])
    else:
        x = math.atan2(rotation[2][1], rotation[1][1])
        z = 0.0
    return [math.degrees(x), math.degrees(y), math.degrees(z)]


def _rotate_vector(vector: list[float], rotation: list[float]) -> list[float]:
    matrix = _rotation_matrix(rotation)
    return [sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3)]
