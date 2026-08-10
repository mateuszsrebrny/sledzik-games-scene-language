from __future__ import annotations

import math


def spherical_cap_geometry(
    base_radius: float,
    height: float,
    segments: int,
) -> tuple[list[tuple[float, float, float]], list[int]]:
    """Return a spherical cap mesh centered on the origin."""
    half_height = height / 2
    sphere_radius = (base_radius**2 + height**2) / (2 * height)
    sphere_center_y = -half_height + height - sphere_radius
    vertices: list[tuple[float, float, float]] = []

    for stack in range(segments):
        y = -half_height + height * stack / segments
        radius = math.sqrt(max(0.0, sphere_radius**2 - (y - sphere_center_y) ** 2))
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), y, radius * math.sin(angle)))

    bottom_center = len(vertices)
    vertices.append((0.0, -half_height, 0.0))
    top_center = len(vertices)
    vertices.append((0.0, half_height, 0.0))

    indices: list[int] = []
    for index in range(segments):
        next_index = (index + 1) % segments
        indices.extend((bottom_center, next_index, index))

    for stack in range(segments - 1):
        current = stack * segments
        next_ring = (stack + 1) * segments
        for index in range(segments):
            next_index = (index + 1) % segments
            indices.extend(
                (
                    current + index,
                    current + next_index,
                    next_ring + next_index,
                    current + index,
                    next_ring + next_index,
                    next_ring + index,
                )
            )

    last_ring = (segments - 1) * segments
    for index in range(segments):
        next_index = (index + 1) % segments
        indices.extend((last_ring + index, last_ring + next_index, top_center))

    return vertices, indices
