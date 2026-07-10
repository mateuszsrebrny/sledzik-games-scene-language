from __future__ import annotations

from pathlib import Path

from lark import Lark

from sgsl.transformer import SGSLTransformer


class SGSLValidationError(ValueError):
    pass


def _load_grammar() -> str:
    return Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8")


_PARSER = Lark(_load_grammar(), start="start", parser="lalr")


def parse_text(source: str) -> dict:
    tree = _PARSER.parse(source)
    scene = SGSLTransformer().transform(tree)
    _validate_scene(scene)
    _resolve_scene(scene)
    return scene


def parse_file(path: str | Path) -> dict:
    file_path = Path(path)
    return parse_text(file_path.read_text(encoding="utf-8"))


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
