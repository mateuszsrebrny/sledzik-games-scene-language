COLORS = {
    "red": "#d83a34",
    "white": "#ffffff",
    "darkgray": "#5a5a5a",
    "gray": "#969696",
    "steelgray": "#8a949e",
    "lightgray": "#d2d2d2",
    "blue": "#3278ff",
}


def resolve_color(color: str) -> str:
    if color.startswith("#"):
        return color.lower()
    try:
        return COLORS[color].lower()
    except KeyError as exc:
        raise ValueError(f"Unknown color: {color}") from exc


def color_to_rgb(color: str) -> tuple[int, int, int]:
    resolved = resolve_color(color).lstrip("#")
    return (
        int(resolved[0:2], 16),
        int(resolved[2:4], 16),
        int(resolved[4:6], 16),
    )
