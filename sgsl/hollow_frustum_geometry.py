from __future__ import annotations

import math


def hollow_frustum_geometry(outer_bottom_radius, outer_top_radius, inner_bottom_radius, inner_top_radius, height, segments):
    """Return the wall mesh shared by the HTML and GLB renderers."""
    half_height = height / 2
    vertices = []
    for y, radius in (
        (-half_height, outer_bottom_radius),
        (half_height, outer_top_radius),
        (-half_height, inner_bottom_radius),
        (half_height, inner_top_radius),
    ):
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((radius * math.cos(angle), y, radius * math.sin(angle)))

    outer_bottom, outer_top = 0, segments
    inner_bottom, inner_top = segments * 2, segments * 3
    indices = []
    for index in range(segments):
        next_index = (index + 1) % segments
        ob, obn = outer_bottom + index, outer_bottom + next_index
        ot, otn = outer_top + index, outer_top + next_index
        ib, ibn = inner_bottom + index, inner_bottom + next_index
        it, itn = inner_top + index, inner_top + next_index
        indices.extend((ob, obn, otn, ob, otn, ot))
        indices.extend((ib, itn, ibn, ib, it, itn))
        indices.extend((ot, otn, itn, ot, itn, it))
        indices.extend((ob, ibn, obn, ob, ib, ibn))
    return vertices, indices
