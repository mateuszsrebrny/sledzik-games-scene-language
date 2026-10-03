from __future__ import annotations


def signed_volume(vertices, indices) -> float:
    """Volume enclosed by a closed triangle mesh, positive when it faces out.

    Each triangle contributes the signed volume of the tetrahedron it forms
    with the origin. For a closed, consistently wound mesh those add up to the
    enclosed volume whatever the origin, positive when the triangles are
    counter-clockwise seen from outside - the glTF front-face convention.
    """
    total = 0.0
    for offset in range(0, len(indices), 3):
        ax, ay, az = vertices[indices[offset]]
        bx, by, bz = vertices[indices[offset + 1]]
        cx, cy, cz = vertices[indices[offset + 2]]
        total += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return total / 6


def orient_outward(vertices, indices) -> list[int]:
    """Return `indices` wound so every triangle faces out of the solid.

    Roblox draws only a triangle's front face and ignores glTF's doubleSided,
    so a mesh wound the other way renders inside out: the near wall vanishes
    and the far wall's interior shows through it, which reads as a solid you
    can see into. The HTML preview's three.js materials cull the same way.

    Decided from the finished mesh rather than by fixing each generator's
    index order, because for several generators the handedness depends on
    their parameters - a pipeArc with a negative angle sweeps through a
    mirrored frame, and a profileRevolve listed top-down revolves the other
    way - so any fixed order would be right for one call and wrong for the
    next. The mesh must already be closed and consistently wound for the sign
    to mean anything.
    """
    if signed_volume(vertices, indices) >= 0:
        return list(indices)
    flipped: list[int] = []
    for offset in range(0, len(indices), 3):
        flipped.extend((indices[offset], indices[offset + 2], indices[offset + 1]))
    return flipped
