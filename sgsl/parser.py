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
        _validate_block(obj)


def _validate_block(obj: dict) -> None:
    if obj.get("type") != "block":
        raise SGSLValidationError(f"Unsupported object type: {obj.get('type')}")
    missing = [field for field in ("at", "size", "color") if field not in obj]
    if missing:
        joined = ", ".join(missing)
        raise SGSLValidationError(f"Block {obj.get('name', '<unnamed>')} is missing: {joined}")
    _validate_anchor(obj)


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


def _resolve_scene(scene: dict) -> None:
    for obj in scene.get("objects", []):
        obj["position"] = _resolve_block_position(obj)


def _resolve_block_position(obj: dict) -> list[float]:
    at_x, at_y, at_z = obj["at"]
    size_x, size_y, size_z = obj["size"]
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
