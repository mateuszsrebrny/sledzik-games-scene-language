from __future__ import annotations

import math


def hollow_pipe_arc_geometry(
    outer_radius,
    inner_radius,
    bend_radius,
    angle,
    segments,
    start_angle=0.0,
    cross_start_angle=0.0,
    cross_angle=180.0,
):
    """Return a shared mesh for an open, hollow pipe following an arc."""
    path_count = segments + 1
    cross_count = segments + 1
    path_start = math.radians(start_angle)
    path_sweep = math.radians(angle)
    cross_start = math.radians(cross_start_angle)
    cross_sweep = math.radians(cross_angle)

    vertices = []
    for path_index in range(path_count):
        path_fraction = path_index / segments
        path_angle = path_start + path_sweep * path_fraction
        center = (bend_radius * math.cos(path_angle), bend_radius * math.sin(path_angle), 0.0)
        normal = (math.cos(path_angle), math.sin(path_angle), 0.0)
        binormal = (0.0, 0.0, 1.0)
        for radius in (outer_radius, inner_radius):
            for cross_index in range(cross_count):
                cross_fraction = cross_index / segments
                cross_angle_value = cross_start + cross_sweep * cross_fraction
                direction = (
                    normal[0] * math.cos(cross_angle_value),
                    normal[1] * math.cos(cross_angle_value),
                    binormal[2] * math.sin(cross_angle_value),
                )
                vertices.append(tuple(center[axis] + radius * direction[axis] for axis in range(3)))

    ring_size = cross_count * 2
    indices = []
    for path_index in range(segments):
        current = path_index * ring_size
        next_ring = (path_index + 1) * ring_size
        for cross_index in range(segments):
            next_cross = cross_index + 1
            outer_a, outer_b = current + cross_index, current + next_cross
            outer_c, outer_d = next_ring + next_cross, next_ring + cross_index
            inner_a, inner_b = current + cross_count + cross_index, current + cross_count + next_cross
            inner_c, inner_d = next_ring + cross_count + next_cross, next_ring + cross_count + cross_index
            indices.extend((outer_a, outer_b, outer_c, outer_a, outer_c, outer_d))
            indices.extend((inner_a, inner_c, inner_b, inner_a, inner_d, inner_c))

        first_outer, first_inner = current, current + cross_count
        last_outer, last_inner = current + segments, current + cross_count + segments
        next_first_outer, next_first_inner = next_ring, next_ring + cross_count
        next_last_outer, next_last_inner = next_ring + segments, next_ring + cross_count + segments
        indices.extend((first_outer, next_first_outer, next_first_inner, first_outer, next_first_inner, first_inner))
        indices.extend((last_outer, last_inner, next_last_inner, last_outer, next_last_inner, next_last_outer))

    for outer, inner in ((0, cross_count), (segments * ring_size, segments * ring_size + cross_count)):
        for cross_index in range(segments):
            next_cross = cross_index + 1
            outer_a, outer_b = outer + cross_index, outer + next_cross
            inner_a, inner_b = inner + cross_index, inner + next_cross
            indices.extend((outer_a, inner_a, inner_b, outer_a, inner_b, outer_b))

    return vertices, indices
