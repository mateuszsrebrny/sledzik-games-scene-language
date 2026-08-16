from __future__ import annotations

import json
import math
import struct
from collections import OrderedDict
from pathlib import Path

from sgsl.colors import color_to_rgb, resolve_color
from sgsl.frustum_geometry import frustum_geometry
from sgsl.parser import SGSLValidationError
from sgsl.primitives import iter_render_objects
from sgsl.hollow_frustum_geometry import hollow_frustum_geometry
from sgsl.hollow_pipe_arc_geometry import hollow_pipe_arc_geometry
from sgsl.pipe_arc_geometry import pipe_arc_geometry
from sgsl.profile_revolve_geometry import profile_revolve_geometry
from sgsl.spherical_cap_geometry import spherical_cap_geometry
from sgsl.sphere_geometry import sphere_geometry
from sgsl.runtime_assets import write_manifest


def write(
    scene: dict,
    output_path: str | Path,
    *,
    merge_ungrouped_materials: bool = False,
) -> Path:
    groups: OrderedDict[str, list[dict]] = OrderedDict()
    markers: list[dict] = []
    material_group_names: dict[tuple, str] = {}
    for obj in iter_render_objects(
        scene,
        expand_pipe_arcs=False,
        expand_frustums=False,
        expand_spherical_caps=False,
    ):
        if obj["type"] == "marker":
            markers.append(obj)
            continue
        key = obj.get("mesh_group")
        if key is None and merge_ungrouped_materials:
            material_key = _material_key(obj)
            key = material_group_names.get(material_key)
            if key is None:
                key = f"MaterialGroup_{len(material_group_names) + 1}"
                material_group_names[material_key] = key
        key = key or obj["name"]
        groups.setdefault(key, []).append(obj)

    binary = bytearray()
    buffer_views: list[dict] = []
    accessors: list[dict] = []
    meshes: list[dict] = []
    nodes: list[dict] = []
    materials: list[dict] = []

    for group_name, objects in groups.items():
        material_key = _material_key(objects[0])
        for obj in objects[1:]:
            if _material_key(obj) != material_key:
                raise SGSLValidationError(
                    f"Mesh group {_short_name(group_name)!r} contains multiple materials. "
                    "Split the geometry into separate mesh groups."
                )

        positions: list[tuple[float, float, float]] = []
        normals: list[tuple[float, float, float]] = []
        colors: list[tuple[float, float, float, float]] = []
        indices: list[int] = []
        exports_normals = all(obj["type"] == "sphere" for obj in objects)
        for obj in objects:
            local_positions, local_indices = _geometry(obj)
            base_index = len(positions)
            positions.extend(_transform_vertices(local_positions, obj["position"], obj["rotation"]))
            if exports_normals:
                normals.extend(_transform_directions(_sphere_normals(local_positions), obj["rotation"]))
            red, green, blue = color_to_rgb(obj["color"])
            alpha = 1.0 - obj["transparency"]
            colors.extend(
                (red / 255, green / 255, blue / 255, alpha)
                for _ in local_positions
            )
            indices.extend(base_index + index for index in local_indices)

        position_bytes = b"".join(struct.pack("<3f", *position) for position in positions)
        position_view = _append_buffer(binary, position_bytes, buffer_views, target=34962)
        mins = [min(position[axis] for position in positions) for axis in range(3)]
        maxs = [max(position[axis] for position in positions) for axis in range(3)]
        position_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": position_view,
                "componentType": 5126,
                "count": len(positions),
                "type": "VEC3",
                "min": mins,
                "max": maxs,
            }
        )

        normal_accessor = None
        if exports_normals:
            normal_bytes = b"".join(struct.pack("<3f", *normal) for normal in normals)
            normal_view = _append_buffer(binary, normal_bytes, buffer_views, target=34962)
            normal_accessor = len(accessors)
            accessors.append(
                {
                    "bufferView": normal_view,
                    "componentType": 5126,
                    "count": len(normals),
                    "type": "VEC3",
                }
            )

        color_bytes = b"".join(struct.pack("<4f", *color) for color in colors)
        color_view = _append_buffer(binary, color_bytes, buffer_views, target=34962)
        color_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": color_view,
                "componentType": 5126,
                "count": len(colors),
                "type": "VEC4",
            }
        )

        index_bytes = b"".join(struct.pack("<I", index) for index in indices)
        index_view = _append_buffer(binary, index_bytes, buffer_views, target=34963)
        index_accessor = len(accessors)
        accessors.append(
            {
                "bufferView": index_view,
                "componentType": 5125,
                "count": len(indices),
                "type": "SCALAR",
                "min": [min(indices)],
                "max": [max(indices)],
            }
        )

        material_index = len(materials)
        materials.append(_material(objects[0], _short_name(group_name)))
        mesh_index = len(meshes)
        attributes = {"POSITION": position_accessor, "COLOR_0": color_accessor}
        if normal_accessor is not None:
            attributes["NORMAL"] = normal_accessor
        meshes.append(
            {
                "name": _short_name(group_name),
                "primitives": [
                    {
                        "attributes": attributes,
                        "indices": index_accessor,
                        "material": material_index,
                    }
                ],
            }
        )
        nodes.append({"name": _short_name(group_name), "mesh": mesh_index})

    marker_mesh = _append_marker_mesh(binary, buffer_views, accessors, meshes, materials) if markers else None
    for marker in markers:
        nodes.append({
            "name": _short_name(marker["name"]),
            "mesh": marker_mesh,
            "translation": marker["position"],
            "rotation": _quaternion_from_euler(marker["rotation"]),
            "extras": {"sgslType": "marker"},
        })

    payload = {
        "asset": {"version": "2.0", "generator": "SGSL"},
        "scene": 0,
        "scenes": [{"name": scene["scene"], "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    json_chunk = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    binary += b"\0" * ((4 - len(binary) % 4) % 4)
    total_length = 12 + 8 + len(json_chunk) + 8 + len(binary)
    glb = (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(glb)
    write_manifest(scene, path.with_suffix(".manifest.json"))
    return path


def _append_marker_mesh(binary, buffer_views, accessors, meshes, materials) -> int:
    # Roblox's 3D Importer discards empty glTF nodes. Give every SGSL marker a
    # shared transparent cube so its name and transform survive as an imported
    # descendant without producing visible scene geometry (it stays fully
    # transparent via the material alpha below, and Roblox-side code also
    # forces Transparency to 1 explicitly). The cube used to be 0.01 studs -
    # small enough that Roblox's importer appeared to lose or corrupt the
    # node's rotation (and sometimes position) when decomposing its transform
    # matrix on import, even though the exported glTF node data is correct.
    # Bumped up well past that precision cliff; still tiny relative to any
    # real scene geometry.
    positions, indices = _block_geometry([0.3, 0.3, 0.3])
    position_bytes = b"".join(struct.pack("<3f", *position) for position in positions)
    position_view = _append_buffer(binary, position_bytes, buffer_views, target=34962)
    position_accessor = len(accessors)
    accessors.append({
        "bufferView": position_view,
        "componentType": 5126,
        "count": len(positions),
        "type": "VEC3",
        "min": [min(position[axis] for position in positions) for axis in range(3)],
        "max": [max(position[axis] for position in positions) for axis in range(3)],
    })

    colors = [(1.0, 1.0, 1.0, 0.0) for _ in positions]
    color_bytes = b"".join(struct.pack("<4f", *color) for color in colors)
    color_view = _append_buffer(binary, color_bytes, buffer_views, target=34962)
    color_accessor = len(accessors)
    accessors.append({
        "bufferView": color_view,
        "componentType": 5126,
        "count": len(colors),
        "type": "VEC4",
    })

    index_bytes = b"".join(struct.pack("<I", index) for index in indices)
    index_view = _append_buffer(binary, index_bytes, buffer_views, target=34963)
    index_accessor = len(accessors)
    accessors.append({
        "bufferView": index_view,
        "componentType": 5125,
        "count": len(indices),
        "type": "SCALAR",
        "min": [min(indices)],
        "max": [max(indices)],
    })

    material_index = len(materials)
    materials.append({
        "name": "SGSLMarkerMaterial",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 1.0, 1.0, 0.0],
            "metallicFactor": 0,
            "roughnessFactor": 1,
        },
        "doubleSided": True,
        "alphaMode": "BLEND",
    })
    mesh_index = len(meshes)
    meshes.append({
        "name": "SGSLMarker",
        "primitives": [{
            "attributes": {"POSITION": position_accessor, "COLOR_0": color_accessor},
            "indices": index_accessor,
            "material": material_index,
        }],
    })
    return mesh_index


def _append_buffer(binary: bytearray, data: bytes, views: list[dict], *, target: int) -> int:
    binary.extend(b"\0" * ((4 - len(binary) % 4) % 4))
    offset = len(binary)
    binary.extend(data)
    views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
    return len(views) - 1


def _geometry(obj: dict) -> tuple[list[tuple[float, float, float]], list[int]]:
    if obj["type"] == "block":
        return _block_geometry(obj["size"])
    if obj["type"] == "wedge":
        return _wedge_geometry(obj["size"])
    if obj["type"] == "cylinder":
        return _cylinder_geometry(obj["radius"], obj["height"], obj.get("segments", 24))
    if obj["type"] == "frustum":
        return frustum_geometry(obj["radius_bottom"], obj["radius_top"], obj["height"], obj["segments"])
    if obj["type"] == "spherical_cap":
        return spherical_cap_geometry(obj["base_radius"], obj["height"], obj["segments"])
    if obj["type"] == "sphere":
        return sphere_geometry(obj["radius"], obj["segments"])
    if obj["type"] == "hollow_frustum":
        return hollow_frustum_geometry(
            obj["outer_bottom_radius"], obj["outer_top_radius"],
            obj["inner_bottom_radius"], obj["inner_top_radius"],
            obj["height"], obj["segments"], obj["start_angle"], obj["angle"],
        )
    if obj["type"] == "hollow_pipe_arc":
        return hollow_pipe_arc_geometry(
            obj["outer_radius"], obj["inner_radius"], obj["bend_radius"],
            obj["angle"], obj["segments"], obj["start_angle"],
            obj["cross_start_angle"], obj["cross_angle"],
        )
    if obj["type"] == "pipe_arc":
        return pipe_arc_geometry(
            obj["pipe_radius"], obj["bend_radius"], obj["angle"], obj["segments"]
        )
    if obj["type"] == "profile_revolve":
        return profile_revolve_geometry(obj["profile"], obj["segments"], obj.get("thickness"))
    raise SGSLValidationError(f"GLB renderer does not support {obj['type']!r}")


def _block_geometry(size: list[float]) -> tuple[list[tuple[float, float, float]], list[int]]:
    x, y, z = (value / 2 for value in size)
    vertices = [
        (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
        (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z),
    ]
    indices = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4,
               3, 7, 6, 3, 6, 2, 0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5]
    return vertices, indices


def _wedge_geometry(size: list[float]) -> tuple[list[tuple[float, float, float]], list[int]]:
    x, y, z = (value / 2 for value in size)
    vertices = [
        (-x, -y, -z), (-x, -y, z), (-x, y, z),
        (x, -y, -z), (x, -y, z), (x, y, z),
    ]
    indices = [
        0, 1, 2,
        3, 5, 4,
        0, 3, 4, 0, 4, 1,
        1, 4, 5, 1, 5, 2,
        0, 2, 5, 0, 5, 3,
    ]
    return vertices, indices


def _cylinder_geometry(radius: float, height: float, segments: int = 24):
    half = height / 2
    vertices = [(0.0, -half, 0.0), (0.0, half, 0.0)]
    for index in range(segments):
        angle = 2 * math.pi * index / segments
        x, z = radius * math.cos(angle), radius * math.sin(angle)
        vertices.extend([(x, -half, z), (x, half, z)])
    indices: list[int] = []
    for index in range(segments):
        next_index = (index + 1) % segments
        bottom, top = 2 + index * 2, 3 + index * 2
        next_bottom, next_top = 2 + next_index * 2, 3 + next_index * 2
        indices.extend([bottom, next_top, top, bottom, next_bottom, next_top])
        indices.extend([0, next_bottom, bottom, 1, top, next_top])
    return vertices, indices


def _transform_vertices(vertices, position, rotation):
    matrix = _rotation_matrix(rotation)
    return [
        tuple(position[row] + sum(matrix[row][column] * vertex[column] for column in range(3)) for row in range(3))
        for vertex in vertices
    ]


def _transform_directions(directions, rotation):
    matrix = _rotation_matrix(rotation)
    return [
        tuple(sum(matrix[row][column] * direction[column] for column in range(3)) for row in range(3))
        for direction in directions
    ]


def _sphere_normals(vertices):
    return [
        tuple(component / math.sqrt(sum(value * value for value in vertex)) for component in vertex)
        for vertex in vertices
    ]


def _rotation_matrix(rotation):
    rx, ry, rz = (math.radians(value) for value in rotation)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return [
        [cy * cz, -cy * sz, sy],
        [sx * sy * cz + cx * sz, -sx * sy * sz + cx * cz, -sx * cy],
        [-cx * sy * cz + sx * sz, cx * sy * sz + sx * cz, cx * cy],
    ]


def _material_key(obj: dict):
    return resolve_color(obj["color"]), obj["material"], obj["transparency"], obj["emissive"]


def _material(obj: dict, name: str) -> dict:
    red, green, blue = color_to_rgb(obj["color"])
    alpha = 1.0 - obj["transparency"]
    roughness_by_material = {
        "asphalt": 0.95,
        "brick": 0.9,
        "cobblestone": 0.9,
        "concrete": 0.8,
        "fabric": 1.0,
        "grass": 1.0,
        "glass": 0.2,
        "metal": 0.32,
        "pavement": 0.85,
        "smoothPlastic": 0.65,
        "woodPlanks": 0.9,
    }
    material = {
        "name": f"{name}Material",
        "pbrMetallicRoughness": {
            "baseColorFactor": [red / 255, green / 255, blue / 255, alpha],
            "metallicFactor": 1 if obj["material"] == "metal" else 0,
            "roughnessFactor": roughness_by_material.get(obj["material"], 0.65),
        },
        "doubleSided": True,
        "alphaMode": "OPAQUE",
    }
    if alpha < 1:
        material["alphaMode"] = "BLEND"
    if obj["emissive"] > 0:
        strength = obj["emissive"]
        material["emissiveFactor"] = [min(1.0, red / 255 * strength), min(1.0, green / 255 * strength), min(1.0, blue / 255 * strength)]
    return material


def _short_name(name: str) -> str:
    return name.rsplit(".", 1)[-1]


def _quaternion_from_euler(rotation: list[float]) -> list[float]:
    """Convert SGSL's XYZ Euler degrees to a glTF quaternion."""
    rx, ry, rz = (math.radians(value) * 0.5 for value in rotation)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    return [
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz,
        cx * cy * cz + sx * sy * sz,
    ]
