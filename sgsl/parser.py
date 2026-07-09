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
