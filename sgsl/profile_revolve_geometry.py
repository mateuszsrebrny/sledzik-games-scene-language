from __future__ import annotations

import math


def profile_revolve_geometry(
    profile: list[tuple[float, float]],
    segments: int,
    thickness: float | None = None,
):
    """Return a continuous mesh made by revolving a radial height profile."""
    profile_center = (profile[0][0] + profile[-1][0]) / 2
    ring_count = segments
    vertices: list[tuple[float, float, float]] = []

    for height, radius in profile:
        for index in range(ring_count):
            angle = (2 * math.pi * index) / segments
            vertices.append((radius * math.cos(angle), height - profile_center, radius * math.sin(angle)))

    indices: list[int] = []
    profile_count = len(profile)
    for profile_index in range(profile_count - 1):
        bottom = profile_index * ring_count
        top = (profile_index + 1) * ring_count
        for index in range(segments):
            next_index = (index + 1) % ring_count
            indices.extend((bottom + index, bottom + next_index, top + next_index))
            indices.extend((bottom + index, top + next_index, top + index))

    if thickness is None:
        bottom_center = len(vertices)
        top_center = bottom_center + 1
        vertices.extend(
            (
                (0.0, profile[0][0] - profile_center, 0.0),
                (0.0, profile[-1][0] - profile_center, 0.0),
            )
        )
        top = (profile_count - 1) * ring_count
        for index in range(segments):
            next_index = (index + 1) % ring_count
            indices.extend((bottom_center, next_index, index))
            indices.extend((top_center, top + index, top + next_index))
    else:
        inner_start = len(vertices)
        for height, radius in profile:
            inner_radius = radius - thickness
            for index in range(ring_count):
                angle = (2 * math.pi * index) / segments
                vertices.append(
                    (
                        inner_radius * math.cos(angle),
                        height - profile_center,
                        inner_radius * math.sin(angle),
                    )
                )

        for profile_index in range(profile_count - 1):
            bottom = inner_start + profile_index * ring_count
            top = inner_start + (profile_index + 1) * ring_count
            for index in range(segments):
                next_index = (index + 1) % ring_count
                indices.extend((bottom + index, top + next_index, bottom + next_index))
                indices.extend((bottom + index, top + index, top + next_index))

        outer_bottom = 0
        outer_top = (profile_count - 1) * ring_count
        inner_bottom = inner_start
        inner_top = inner_start + (profile_count - 1) * ring_count
        for index in range(segments):
            next_index = (index + 1) % ring_count
            indices.extend((outer_top + index, outer_top + next_index, inner_top + next_index))
            indices.extend((outer_top + index, inner_top + next_index, inner_top + index))
            indices.extend((outer_bottom + index, inner_bottom + next_index, outer_bottom + next_index))
            indices.extend((outer_bottom + index, inner_bottom + index, inner_bottom + next_index))

    return vertices, indices
