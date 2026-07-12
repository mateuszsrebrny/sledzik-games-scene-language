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


def parse_text(source: str) -> dict:
    raw_scene = _parse_source_blocks(source)
    scene = _expand_scene(raw_scene)
    _validate_scene(scene)
    _resolve_scene(scene)
    return scene


def parse_file(path: str | Path) -> dict:
    file_path = Path(path)
    return parse_text(file_path.read_text(encoding="utf-8"))


def _parse_source_blocks(source: str) -> dict:
    lines = source.splitlines()
    scene_name = _parse_scene_name(lines)
    statements = []
    for block in _split_top_level_blocks(lines[1:]):
        tree = _STATEMENT_PARSER.parse(block)
        statements.append(SGSLTransformer().transform(tree))
    return {
        "scene": scene_name,
        "statements": statements,
    }


def _parse_scene_name(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.fullmatch(r"scene\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
        if not match:
            raise SGSLValidationError("Expected first top-level statement to be 'scene <Name>'.")
        return match.group(1)
    raise SGSLValidationError("Scene name is missing.")


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
        statement_type = statement["type"]
        if statement_type == "component_definition":
            if statement["name"] in components:
                raise SGSLValidationError(f"Duplicate component definition {statement['name']!r}.")
            components[statement["name"]] = statement
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


def _expand_instance(instance: dict, components: dict[str, dict]) -> list[dict]:
    component_name = instance["component"]
    try:
        component = components[component_name]
    except KeyError as exc:
        raise SGSLValidationError(
            f"Instance {instance['name']!r} references unknown component {component_name!r}."
        ) from exc

    parameter_values = _resolve_component_parameters(component, instance)
    instance_at = _evaluate_vector(instance.get("at", [_number_node(0), _number_node(0), _number_node(0)]), parameter_values)
    instance_rotation = _evaluate_vector(
        instance.get("rotation", [_number_node(0), _number_node(0), _number_node(0)]),
        parameter_values,
    )

    expanded: list[dict] = []
    for template in component["objects"]:
        obj = copy.deepcopy(template)
        _evaluate_object_expressions(obj, parameter_values)
        _resolve_scene({"objects": [obj]})
        obj["position"] = _apply_instance_transform(obj["position"], instance_at, instance_rotation)
        obj["at"] = obj["position"]
        obj["anchor"] = ["center", "center", "center"]
        obj["rotation"] = _compose_rotations(instance_rotation, obj["rotation"])
        obj["name"] = f"{instance['name']}.{obj['name']}"
        expanded.append(obj)

    return expanded


def _resolve_component_parameters(component: dict, instance: dict) -> dict[str, float]:
    values: dict[str, float] = {}
    parameter_names = [param["name"] for param in component["parameters"]]

    for param in component["parameters"]:
        values[param["name"]] = _evaluate_expression(param["value"], values)

    for name, expression in instance["parameter_overrides"].items():
        if name not in parameter_names:
            available = ", ".join(parameter_names)
            raise SGSLValidationError(
                f"Instance {instance['name']!r} of component {component['name']!r} "
                f"sets unknown parameter {name!r}. Available parameters: {available}"
            )
        values[name] = _evaluate_expression(expression, values)

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
    if "height" in obj:
        obj["height"] = _evaluate_expression(obj["height"], environment)
    if "segments" in obj:
        obj["segments"] = _evaluate_expression(obj["segments"], environment)
    if "transparency" in obj:
        obj["transparency"] = _evaluate_expression(obj["transparency"], environment)
    else:
        obj["transparency"] = 0.0


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


def _apply_instance_transform(local_position: list[float], instance_at: list[float], instance_rotation: list[float]) -> list[float]:
    rotated = _rotate_vector(local_position, instance_rotation)
    return [
        instance_at[0] + rotated[0],
        instance_at[1] + rotated[1],
        instance_at[2] + rotated[2],
    ]


def _rotate_vector(vector: list[float], rotation: list[float]) -> list[float]:
    x, y, z = vector
    rx, ry, rz = (math.radians(value) for value in rotation)

    cos_x, sin_x = math.cos(rx), math.sin(rx)
    y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x

    cos_y, sin_y = math.cos(ry), math.sin(ry)
    x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y

    cos_z, sin_z = math.cos(rz), math.sin(rz)
    x, y = x * cos_z - y * sin_z, x * sin_z + y * cos_z

    return [x, y, z]


def _compose_rotations(instance_rotation: list[float], local_rotation: list[float]) -> list[float]:
    return [
        instance_rotation[0] + local_rotation[0],
        instance_rotation[1] + local_rotation[1],
        instance_rotation[2] + local_rotation[2],
    ]


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
    else:
        raise SGSLValidationError(f"Unsupported object type: {object_type}")

    _validate_anchor(obj)
    _validate_rotation(obj)
    _validate_transparency(obj)


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


def _resolve_scene(scene: dict) -> None:
    for obj in scene.get("objects", []):
        obj["position"] = _resolve_position(obj)


def _resolve_position(obj: dict) -> list[float]:
    at_x, at_y, at_z = obj["at"]
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

    max_radius = max(obj["radius_bottom"], obj["radius_top"])
    diameter = max_radius * 2
    return diameter, obj["height"], diameter
