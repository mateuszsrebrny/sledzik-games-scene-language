from __future__ import annotations

import math


def pipe_arc_geometry(
    pipe_radius: float,
    bend_radius: float,
    angle: float,
    segments: int,
):
    """Return a capped solid tube swept along the standard pipeArc path."""
    path_count = segments + 1
    cross_count = segments
    sweep = math.radians(abs(angle))
    direction = 1.0 if angle >= 0 else -1.0

    vertices = []
    for path_index in range(path_count):
        fraction = path_index / segments
        path_angle = sweep * fraction
        center = (
            bend_radius * math.sin(path_angle),
            direction * bend_radius * (1.0 - math.cos(path_angle)),
            0.0,
        )
        normal = (
            math.sin(path_angle),
            -direction * math.cos(path_angle),
            0.0,
        )
        binormal = (0.0, 0.0, 1.0)
        for cross_index in range(cross_count):
            cross_angle = 2.0 * math.pi * cross_index / cross_count
            offset = (
                pipe_radius * (normal[0] * math.cos(cross_angle) + binormal[0] * math.sin(cross_angle)),
                pipe_radius * (normal[1] * math.cos(cross_angle) + binormal[1] * math.sin(cross_angle)),
                pipe_radius * (normal[2] * math.cos(cross_angle) + binormal[2] * math.sin(cross_angle)),
            )
            vertices.append(tuple(center[axis] + offset[axis] for axis in range(3)))

    indices = []
    for path_index in range(segments):
        current = path_index * cross_count
        next_ring = (path_index + 1) * cross_count
        for cross_index in range(cross_count):
            next_cross = (cross_index + 1) % cross_count
            a, b = current + cross_index, current + next_cross
            c, d = next_ring + next_cross, next_ring + cross_index
            indices.extend((a, b, c, a, c, d))

    start_center = len(vertices)
    vertices.append((0.0, 0.0, 0.0))
    end_center = len(vertices)
    end_angle = sweep
    vertices.append(
        (
            bend_radius * math.sin(end_angle),
            direction * bend_radius * (1.0 - math.cos(end_angle)),
            0.0,
        )
    )
    first_ring = 0
    last_ring = segments * cross_count
    for cross_index in range(cross_count):
        next_cross = (cross_index + 1) % cross_count
        indices.extend((start_center, next_cross, cross_index))
        indices.extend((end_center, last_ring + cross_index, last_ring + next_cross))

    return vertices, indices
