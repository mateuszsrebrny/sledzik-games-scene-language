from __future__ import annotations

import math


def sphere_geometry(
    radius: float,
    segments: int,
) -> tuple[list[tuple[float, float, float]], list[int]]:
    """Return a UV sphere mesh centered on the origin."""
    rings = max(2, segments // 2)
    vertices: list[tuple[float, float, float]] = [(0.0, -radius, 0.0)]

    for ring in range(1, rings):
        latitude = -math.pi / 2 + math.pi * ring / rings
        y = radius * math.sin(latitude)
        ring_radius = radius * math.cos(latitude)
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((ring_radius * math.cos(angle), y, ring_radius * math.sin(angle)))

    top_index = len(vertices)
    vertices.append((0.0, radius, 0.0))

    indices: list[int] = []
    first_ring = 1
    for index in range(segments):
        next_index = (index + 1) % segments
        indices.extend((0, first_ring + index, first_ring + next_index))

    for ring in range(rings - 2):
        current = first_ring + ring * segments
        next_ring = current + segments
        for index in range(segments):
            next_index = (index + 1) % segments
            indices.extend(
                (
                    current + index,
                    next_ring + next_index,
                    current + next_index,
                    current + index,
                    next_ring + index,
                    next_ring + next_index,
                )
            )

    last_ring = first_ring + (rings - 2) * segments
    for index in range(segments):
        next_index = (index + 1) % segments
        indices.extend((last_ring + index, top_index, last_ring + next_index))

    return vertices, indices
