from __future__ import annotations

import copy
import math
import re
from pathlib import Path

from lark import Lark

from sgsl.transformer import SGSLTransformer


class SGSLValidationError(ValueError):
    pass


def _load_grammar() -> str:
    return Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8")


_GRAMMAR = _load_grammar()
_PARSER = Lark(_GRAMMAR, start="start", parser="lalr")
_STATEMENT_PARSER = Lark(_GRAMMAR, start="statement", parser="lalr")
_MAX_COMPONENT_DEPTH = 64


def parse_text(source: str) -> dict:
    raw_scene = _parse_source_blocks(source, require_scene=True)
    if any(statement["type"] == "import" for statement in raw_scene["statements"]):
        raise SGSLValidationError("Imports require a source file; use parse_file() instead of parse_text().")
    scene = _expand_scene(raw_scene)
    _validate_scene(scene)
    _resolve_scene(scene)
    return scene


def parse_file(path: str | Path) -> dict:
    raw_scene = _load_import_graph(Path(path))
    scene = _expand_scene(raw_scene)
    _validate_scene(scene)
    _resolve_scene(scene)
    return scene


def _parse_source_blocks(source: str, *, require_scene: bool) -> dict:
    lines = source.splitlines()
    scene_name, statement_lines = _extract_scene(lines)
    if require_scene and scene_name is None:
        raise SGSLValidationError("Scene name is missing.")
    statements = []
    for block in _split_top_level_blocks(statement_lines):
        tree = _STATEMENT_PARSER.parse(block)
        statements.append(SGSLTransformer().transform(tree))
    return {
        "scene": scene_name,
        "statements": statements,
    }


def _extract_scene(lines: list[str]) -> tuple[str | None, list[str]]:
    scene_name: str | None = None
    statement_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        match = re.fullmatch(r"scene\s+([A-Za-z_][A-Za-z0-9_]*)", stripped) if stripped else None
        if match:
            if line.startswith((" ", "\t")):
                raise SGSLValidationError("Scene declaration must be a top-level statement.")
            if scene_name is not None:
                raise SGSLValidationError("A file may declare only one scene.")
            scene_name = match.group(1)
            continue
        statement_lines.append(line)
    return scene_name, statement_lines


def _load_import_graph(entry_path: Path) -> dict:
    entry = entry_path.expanduser().resolve()
    loaded: set[Path] = set()
    active: list[Path] = []

    def load(path: Path, importer: Path | None = None, import_text: str | None = None) -> tuple[str | None, list[dict]]:
        canonical = path.expanduser().resolve()
        if canonical in active:
            cycle_start = active.index(canonical)
            cycle = active[cycle_start:] + [canonical]
            raise SGSLValidationError(
                "Import cycle detected:\n" + " -> ".join(item.name for item in cycle)
            )
        if canonical in loaded:
            return None, []
        if not canonical.is_file():
            if importer is None:
                raise SGSLValidationError(f"SGSL file not found: {canonical}")
            raise SGSLValidationError(
                f"Could not import {import_text!r}\nfrom {str(importer)!r}."
            )

        active.append(canonical)
        raw = _parse_source_blocks(
            canonical.read_text(encoding="utf-8"),
            require_scene=canonical == entry,
        )
        statements: list[dict] = []
        for statement in raw["statements"]:
            if statement["type"] != "import":
                continue
            imported_path = canonical.parent / statement["path"]
            _, imported_statements = load(imported_path, canonical, statement["path"])
            statements.extend(imported_statements)
        for statement in raw["statements"]:
            if statement["type"] == "import":
                continue
            statement["_source_path"] = str(canonical)
            statements.append(statement)
        active.pop()
        loaded.add(canonical)
        return raw["scene"], statements

    scene_name, statements = load(entry)
    return {"scene": scene_name, "statements": statements}


def _split_top_level_blocks(lines: list[str]) -> list[str]:
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        is_top_level = line and not line.startswith((" ", "\t"))
        if is_top_level and stripped and not stripped.startswith("#"):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        blocks.append(current)

    return ["\n".join(block).strip() for block in blocks if any(line.strip() for line in block)]


def _expand_scene(raw_scene: dict) -> dict:
    components: dict[str, dict] = {}
    objects: list[dict] = []
    seen_instance_names: set[str] = set()

    for statement in raw_scene.get("statements", []):
        if statement["type"] != "component_definition":
            continue
        previous = components.get(statement["name"])
        if previous is not None:
            previous_path = previous.get("_source_path", "<input>")
            current_path = statement.get("_source_path", "<input>")
            raise SGSLValidationError(
                f"Component {statement['name']!r} is defined in both:\n"
                f"{previous_path}\n{current_path}"
            )
        components[statement["name"]] = statement

    for statement in raw_scene.get("statements", []):
        statement_type = statement["type"]
        if statement_type == "component_definition":
            continue

        if statement_type == "component_instance":
            if statement["name"] in seen_instance_names:
                raise SGSLValidationError(f"Duplicate instance name {statement['name']!r}.")
            seen_instance_names.add(statement["name"])
            objects.extend(_expand_instance(statement, components))
            continue

        objects.append(_evaluate_top_level_object(statement))

    return {
        "scene": raw_scene["scene"],
        "objects": objects,
    }


def _evaluate_top_level_object(obj: dict) -> dict:
    evaluated = copy.deepcopy(obj)
    _evaluate_object_expressions(evaluated, {})
    return evaluated


def _expand_instance(
    instance: dict,
    components: dict[str, dict],
    parent_transform: list[list[float]] | None = None,
    parent_parameters: dict[str, float] | None = None,
    parent_scale: float = 1.0,
    parent_emissive: float | None = None,
    path: str | None = None,
    depth: int = 0,
) -> list[dict]:
    if depth >= _MAX_COMPONENT_DEPTH:
        raise SGSLValidationError(
            f"Component expansion exceeded maximum nesting depth of {_MAX_COMPONENT_DEPTH}. "
            "Possible recursive component reference."
        )

    component_name = instance["component"]
    try:
        component = components[component_name]
    except KeyError as exc:
        raise SGSLValidationError(
            f"Instance {instance['name']!r} references unknown component {component_name!r}."
        ) from exc

    parent_transform = parent_transform or _identity_transform()
    parent_parameters = parent_parameters or {}
    parameter_values = _resolve_component_parameters(component, instance, parent_parameters)
    expression_environment = {**parameter_values, **parent_parameters}
    instance_at = _evaluate_vector(
        instance.get("at", [_number_node(0), _number_node(0), _number_node(0)]),
        expression_environment,
    )
    instance_rotation = _evaluate_vector(
        instance.get("rotation", [_number_node(0), _number_node(0), _number_node(0)]),
        expression_environment,
    )
    instance_scale = _evaluate_expression(instance.get("scale", _number_node(1)), expression_environment)
    if instance_scale <= 0:
        raise SGSLValidationError(
            f"Instance {instance['name']!r} has invalid scale {instance_scale!r}; expected a positive number"
        )
    world_scale = parent_scale * instance_scale
    instance_emissive = parent_emissive
    if "emissive" in instance:
        instance_emissive = _evaluate_expression(instance["emissive"], expression_environment)
        if instance_emissive < 0:
            raise SGSLValidationError(
                f"Instance {instance['name']!r} has invalid emissive {instance_emissive!r}; "
                "expected a non-negative number"
            )
    world_transform = _multiply_transforms(
        parent_transform,
        _make_transform(instance_at, instance_rotation, instance_scale),
    )
    instance_path = f"{path}.{instance['name']}" if path else instance["name"]

    expanded: list[dict] = []
    for template in component["objects"]:
        if template["type"] == "component_instance":
            expanded.extend(
                _expand_instance(
                    template,
                    components,
                    world_transform,
                    parameter_values,
                    world_scale,
                    instance_emissive,
                    instance_path,
                    depth + 1,
                )
            )
            continue

        obj = copy.deepcopy(template)
        _evaluate_object_expressions(obj, parameter_values)
        if instance_emissive is not None:
            obj["emissive"] = instance_emissive
        _resolve_scene({"objects": [obj]})
        object_transform = _multiply_transforms(
            world_transform,
            _make_transform(obj["position"], obj["rotation"]),
        )
        obj["position"] = _transform_position(object_transform)
        obj["at"] = obj["position"]
        obj["anchor"] = ["center", "center", "center"]
        obj["rotation"] = _transform_rotation(object_transform)
        _scale_object_dimensions(obj, world_scale)
        obj["name"] = f"{instance_path}.{obj['name']}"
        expanded.append(obj)

    return expanded


def _resolve_component_parameters(
    component: dict,
    instance: dict,
    parent_parameters: dict[str, float],
) -> dict[str, float]:
    values: dict[str, float] = {}
    parameter_names = [param["name"] for param in component["parameters"]]

    for param in component["parameters"]:
        values[param["name"]] = _evaluate_expression(param["value"], {**parent_parameters, **values})

    for name, expression in instance["parameter_overrides"].items():
        if name not in parameter_names:
            available = ", ".join(parameter_names)
            raise SGSLValidationError(
                f"Instance {instance['name']!r} of component {component['name']!r} "
                f"sets unknown parameter {name!r}. Available parameters: {available}"
            )
        values[name] = _evaluate_expression(expression, {**values, **parent_parameters})

    return values


def _evaluate_object_expressions(obj: dict, environment: dict[str, float]) -> None:
    if "at" in obj:
        obj["at"] = _evaluate_vector(obj["at"], environment)
    obj.setdefault("anchor", ["center", "center", "center"])
    if "size" in obj:
        obj["size"] = _evaluate_vector(obj["size"], environment)
    if "rotation" in obj:
        obj["rotation"] = _evaluate_vector(obj["rotation"], environment)
    else:
        obj["rotation"] = [0.0, 0.0, 0.0]
    if "radius" in obj:
        obj["radius"] = _evaluate_expression(obj["radius"], environment)
    if "radius_inner" in obj:
        obj["radius_inner"] = _evaluate_expression(obj["radius_inner"], environment)
    if "radius_outer" in obj:
        obj["radius_outer"] = _evaluate_expression(obj["radius_outer"], environment)
    if "radius_top" in obj:
        obj["radius_top"] = _evaluate_expression(obj["radius_top"], environment)
    if "radius_bottom" in obj:
        obj["radius_bottom"] = _evaluate_expression(obj["radius_bottom"], environment)
    if "base_radius" in obj:
        obj["base_radius"] = _evaluate_expression(obj["base_radius"], environment)
    if "pipe_radius" in obj:
        obj["pipe_radius"] = _evaluate_expression(obj["pipe_radius"], environment)
    if "bend_radius" in obj:
        obj["bend_radius"] = _evaluate_expression(obj["bend_radius"], environment)
    if "angle" in obj:
        obj["angle"] = _evaluate_expression(obj["angle"], environment)
    if "height" in obj:
        obj["height"] = _evaluate_expression(obj["height"], environment)
    if "segments" in obj:
        obj["segments"] = _evaluate_expression(obj["segments"], environment)
    if "transparency" in obj:
        obj["transparency"] = _evaluate_expression(obj["transparency"], environment)
    else:
        obj["transparency"] = 0.0
    if "emissive" in obj:
        obj["emissive"] = _evaluate_expression(obj["emissive"], environment)
    else:
        obj["emissive"] = 0.0


def _evaluate_vector(values: list, environment: dict[str, float]) -> list[float]:
    return [_evaluate_expression(value, environment) for value in values]


def _evaluate_expression(node, environment: dict[str, float]) -> float:
    if isinstance(node, (int, float)):
        return float(node)

    kind = node[0]
    if kind == "number":
        return float(node[1])
    if kind == "variable":
        try:
            return float(environment[node[1]])
        except KeyError as exc:
            raise SGSLValidationError(f"Unknown parameter {node[1]!r} in expression.") from exc
    if kind == "add":
        return _evaluate_expression(node[1], environment) + _evaluate_expression(node[2], environment)
    if kind == "sub":
        return _evaluate_expression(node[1], environment) - _evaluate_expression(node[2], environment)
    if kind == "mul":
        return _evaluate_expression(node[1], environment) * _evaluate_expression(node[2], environment)
    if kind == "div":
        return _evaluate_expression(node[1], environment) / _evaluate_expression(node[2], environment)
    if kind == "neg":
        return -_evaluate_expression(node[1], environment)
    raise SGSLValidationError(f"Unsupported expression node: {node!r}")


def _number_node(value: float):
    return ("number", float(value))


def _identity_transform() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _make_transform(
    position: list[float],
    rotation: list[float],
    scale: float = 1.0,
) -> list[list[float]]:
    rx, ry, rz = (math.radians(value) for value in rotation)
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    cos_z, sin_z = math.cos(rz), math.sin(rz)

    return [
        [scale * cos_y * cos_z, -scale * cos_y * sin_z, scale * sin_y, position[0]],
        [scale * (sin_x * sin_y * cos_z + cos_x * sin_z), scale * (-sin_x * sin_y * sin_z + cos_x * cos_z), -scale * sin_x * cos_y, position[1]],
        [scale * (-cos_x * sin_y * cos_z + sin_x * sin_z), scale * (cos_x * sin_y * sin_z + sin_x * cos_z), scale * cos_x * cos_y, position[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _multiply_transforms(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[row][index] * right[index][column] for index in range(4)) for column in range(4)]
        for row in range(4)
    ]


def _transform_position(transform: list[list[float]]) -> list[float]:
    return [transform[0][3], transform[1][3], transform[2][3]]


def _transform_rotation(transform: list[list[float]]) -> list[float]:
    # Match Three.js Euler XYZ and Roblox CFrame.Angles (Rx * Ry * Rz).
    scale = math.sqrt(sum(transform[row][0] ** 2 for row in range(3)))
    rotation = [[transform[row][column] / scale for column in range(3)] for row in range(3)]
    sin_y = max(-1.0, min(1.0, rotation[0][2]))
    y = math.asin(sin_y)
    if abs(math.cos(y)) > 1e-9:
        x = math.atan2(-rotation[1][2], rotation[2][2])
        z = math.atan2(-rotation[0][1], rotation[0][0])
    else:
        x = math.atan2(rotation[2][1], rotation[1][1])
        z = 0.0
    return [math.degrees(x), math.degrees(y), math.degrees(z)]


def _scale_object_dimensions(obj: dict, scale: float) -> None:
    if "size" in obj:
        obj["size"] = [value * scale for value in obj["size"]]
    for field in (
        "radius",
        "radius_inner",
        "radius_outer",
        "radius_top",
        "radius_bottom",
        "base_radius",
        "pipe_radius",
        "bend_radius",
        "height",
    ):
        if field in obj:
            obj[field] *= scale


def _validate_scene(scene: dict) -> None:
    if "scene" not in scene:
        raise SGSLValidationError("Scene name is missing.")
    for obj in scene.get("objects", []):
        _validate_object(obj)


def _validate_object(obj: dict) -> None:
    object_type = obj.get("type")
    if object_type == "block":
        _validate_required_fields(obj, ("at", "size", "color"))
        _validate_size_triplet(obj, "size")
    elif object_type == "cylinder":
        _validate_required_fields(obj, ("at", "radius", "height", "color"))
        _validate_positive_number(obj, "radius")
        _validate_positive_number(obj, "height")
    elif object_type == "frustum":
        _validate_required_fields(obj, ("at", "radius_bottom", "radius_top", "height", "segments", "color"))
        _validate_positive_number(obj, "radius_bottom")
        _validate_positive_number(obj, "radius_top")
        _validate_positive_number(obj, "height")
        _validate_positive_integer(obj, "segments")
    elif object_type == "ring":
        _validate_required_fields(obj, ("at", "radius_inner", "radius_outer", "height", "segments", "color"))
        _validate_positive_number(obj, "radius_inner")
        _validate_positive_number(obj, "radius_outer")
        _validate_positive_number(obj, "height")
        _validate_positive_integer(obj, "segments")
        if obj["radius_inner"] >= obj["radius_outer"]:
            raise SGSLValidationError(
                f"Ring {obj['name']} has invalid radii; radius_inner must be smaller than radius_outer"
            )
    elif object_type == "spherical_cap":
        _validate_required_fields(obj, ("at", "base_radius", "height", "segments", "color"))
        _validate_positive_number(obj, "base_radius")
        _validate_positive_number(obj, "height")
        _validate_positive_integer(obj, "segments")
    elif object_type == "pipe_arc":
        _validate_required_fields(obj, ("at", "pipe_radius", "bend_radius", "angle", "segments", "color"))
        _validate_positive_number(obj, "pipe_radius")
        _validate_positive_number(obj, "bend_radius")
        _validate_positive_integer(obj, "segments")
        if obj["angle"] == 0:
            raise SGSLValidationError(f"Pipe arc {obj['name']} has invalid angle 0; expected a non-zero angle")
    else:
        raise SGSLValidationError(f"Unsupported object type: {object_type}")

    _validate_anchor(obj)
    _validate_rotation(obj)
    _validate_transparency(obj)
    _validate_emissive(obj)


def _validate_required_fields(obj: dict, fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        joined = ", ".join(missing)
        raise SGSLValidationError(
            f"{obj.get('type', 'object').capitalize()} {obj.get('name', '<unnamed>')} is missing: {joined}"
        )


def _validate_size_triplet(obj: dict, field: str) -> None:
    values = obj[field]
    if len(values) != 3:
        raise SGSLValidationError(
            f"{obj['type'].capitalize()} {obj['name']} must have exactly 3 values for {field}"
        )
    for value in values:
        if value <= 0:
            raise SGSLValidationError(
                f"{obj['type'].capitalize()} {obj['name']} has invalid {field} {values!r}; expected positive numbers"
            )


def _validate_positive_number(obj: dict, field: str) -> None:
    value = obj[field]
    if value <= 0:
        raise SGSLValidationError(
            f"{obj['type'].capitalize()} {obj['name']} has invalid {field} {value!r}; expected a positive number"
        )


def _validate_positive_integer(obj: dict, field: str) -> None:
    value = obj[field]
    if int(value) != value or value <= 0:
        raise SGSLValidationError(
            f"{obj['type'].capitalize()} {obj['name']} has invalid {field} {value!r}; expected a positive integer"
        )
    obj[field] = int(value)


def _validate_anchor(obj: dict) -> None:
    anchor = obj.setdefault("anchor", ["center", "center", "center"])
    allowed_x = {"left", "center", "right"}
    allowed_y = {"bottom", "center", "top"}
    allowed_z = {"front", "center", "back"}

    if len(anchor) != 3:
        raise SGSLValidationError(f"Block {obj['name']} must have exactly 3 anchor values")

    if anchor[0] not in allowed_x:
        raise SGSLValidationError(
            f"Block {obj['name']} has invalid X anchor {anchor[0]!r}; expected left, center, or right"
        )
    if anchor[1] not in allowed_y:
        raise SGSLValidationError(
            f"Block {obj['name']} has invalid Y anchor {anchor[1]!r}; expected bottom, center, or top"
        )
    if anchor[2] not in allowed_z:
        raise SGSLValidationError(
            f"Block {obj['name']} has invalid Z anchor {anchor[2]!r}; expected front, center, or back"
        )


def _validate_rotation(obj: dict) -> None:
    rotation = obj.setdefault("rotation", [0.0, 0.0, 0.0])
    if len(rotation) != 3:
        raise SGSLValidationError(
            f"{obj['type'].capitalize()} {obj['name']} must have exactly 3 rotation values"
        )


def _validate_transparency(obj: dict) -> None:
    transparency = obj.setdefault("transparency", 0.0)
    if not 0.0 <= transparency <= 1.0:
        raise SGSLValidationError(
            f"Block {obj['name']} has invalid transparency {transparency!r}; expected a value from 0.0 to 1.0"
        )


def _validate_emissive(obj: dict) -> None:
    emissive = obj.setdefault("emissive", 0.0)
    if emissive < 0:
        raise SGSLValidationError(
            f"{obj['type'].capitalize()} {obj['name']} has invalid emissive {emissive!r}; "
            "expected a non-negative number"
        )


def _resolve_scene(scene: dict) -> None:
    for obj in scene.get("objects", []):
        obj["position"] = _resolve_position(obj)


def _resolve_position(obj: dict) -> list[float]:
    at_x, at_y, at_z = obj["at"]
    if obj["type"] == "pipe_arc":
        return [at_x, at_y, at_z]

    size_x, size_y, size_z = _get_object_bounds(obj)
    anchor_x, anchor_y, anchor_z = obj["anchor"]

    if anchor_x == "left":
        center_x = at_x + size_x / 2
    elif anchor_x == "right":
        center_x = at_x - size_x / 2
    else:
        center_x = at_x

    if anchor_y == "bottom":
        center_y = at_y + size_y / 2
    elif anchor_y == "top":
        center_y = at_y - size_y / 2
    else:
        center_y = at_y

    if anchor_z == "front":
        center_z = at_z + size_z / 2
    elif anchor_z == "back":
        center_z = at_z - size_z / 2
    else:
        center_z = at_z

    return [center_x, center_y, center_z]


def _get_object_bounds(obj: dict) -> tuple[float, float, float]:
    if obj["type"] == "block":
        size_x, size_y, size_z = obj["size"]
        return size_x, size_y, size_z

    if obj["type"] == "cylinder":
        diameter = obj["radius"] * 2
        return diameter, obj["height"], diameter

    if obj["type"] == "ring":
        diameter = obj["radius_outer"] * 2
        return diameter, obj["height"], diameter

    if obj["type"] == "spherical_cap":
        diameter = obj["base_radius"] * 2
        return diameter, obj["height"], diameter

    if obj["type"] == "pipe_arc":
        diameter = 2 * (obj["bend_radius"] + obj["pipe_radius"])
        return diameter, diameter, obj["pipe_radius"] * 2

    max_radius = max(obj["radius_bottom"], obj["radius_top"])
    diameter = max_radius * 2
    return diameter, obj["height"], diameter
