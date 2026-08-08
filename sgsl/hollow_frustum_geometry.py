from __future__ import annotations

import math


def hollow_frustum_geometry(
    outer_bottom_radius,
    outer_top_radius,
    inner_bottom_radius,
    inner_top_radius,
    height,
    segments,
    start_angle=0.0,
    angle=360.0,
):
    """Return the wall mesh shared by the HTML and GLB renderers."""
    half_height = height / 2
    start_radians = math.radians(start_angle)
    sweep_radians = math.radians(angle)
    is_full = math.isclose(abs(sweep_radians), 2 * math.pi, rel_tol=1e-9, abs_tol=1e-9)
    ring_count = segments if is_full else segments + 1
    vertices = []
    for y, radius in (
        (-half_height, outer_bottom_radius),
        (half_height, outer_top_radius),
        (-half_height, inner_bottom_radius),
        (half_height, inner_top_radius),
    ):
        for index in range(ring_count):
            fraction = index / segments
            current_angle = start_radians + sweep_radians * fraction
            vertices.append((radius * math.cos(current_angle), y, radius * math.sin(current_angle)))

    outer_bottom, outer_top = 0, ring_count
    inner_bottom, inner_top = ring_count * 2, ring_count * 3
    indices = []
    for index in range(segments):
        next_index = (index + 1) % ring_count if is_full else index + 1
        ob, obn = outer_bottom + index, outer_bottom + next_index
        ot, otn = outer_top + index, outer_top + next_index
        ib, ibn = inner_bottom + index, inner_bottom + next_index
        it, itn = inner_top + index, inner_top + next_index
        indices.extend((ob, obn, otn, ob, otn, ot))
        indices.extend((ib, itn, ibn, ib, it, itn))
        indices.extend((ot, otn, itn, ot, itn, it))
        indices.extend((ob, ibn, obn, ob, ib, ibn))

    if not is_full:
        # Close the two radial ends while leaving the axial top and bottom
        # rims intact. This produces an open trough for a 180 degree sweep.
        for index in (0, ring_count - 1):
            ob, ot = outer_bottom + index, outer_top + index
            ib, it = inner_bottom + index, inner_top + index
            indices.extend((ob, ot, it, ob, it, ib))

    return vertices, indices
