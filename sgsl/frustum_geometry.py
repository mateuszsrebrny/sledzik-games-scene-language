from __future__ import annotations

import math


def frustum_geometry(
    bottom_radius: float,
    top_radius: float,
    height: float,
    segments: int,
) -> tuple[list[tuple[float, float, float]], list[int]]:
    """Return a capped, smoothable frustum mesh centered on the origin."""
    half_height = height / 2
    vertices: list[tuple[float, float, float]] = []
    for y, radius in ((-half_height, bottom_radius), (half_height, top_radius)):
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), y, radius * math.sin(angle)))

    bottom_ring = 0
    top_ring = segments
    bottom_center = len(vertices)
    vertices.append((0.0, -half_height, 0.0))
    top_center = len(vertices)
    vertices.append((0.0, half_height, 0.0))

    indices: list[int] = []
    for index in range(segments):
        next_index = (index + 1) % segments
        bottom, bottom_next = bottom_ring + index, bottom_ring + next_index
        top, top_next = top_ring + index, top_ring + next_index
        indices.extend((bottom, bottom_next, top_next, bottom, top_next, top))
        indices.extend((bottom_center, bottom_next, bottom))
        indices.extend((top_center, top, top_next))

    return vertices, indices
