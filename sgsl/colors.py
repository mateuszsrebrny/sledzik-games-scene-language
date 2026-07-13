COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "gray": "#808080",
    "lightgray": "#d2d2d2",
    "darkgray": "#5a5a5a",
    "steelgray": "#8a949e",
    "silver": "#c0c0c0",
    "red": "#d83a34",
    "darkred": "#8b0000",
    "pink": "#ff69b4",
    "purple": "#800080",
    "magenta": "#ff00ff",
    "fuchsia": "#ff00ff",
    "brown": "#8b4513",
    "orange": "#ff9800",
    "gold": "#ffd700",
    "yellow": "#ffeb3b",
    "olive": "#808000",
    "green": "#4caf50",
    "lime": "#00ff00",
    "teal": "#008080",
    "cyan": "#00ffff",
    "aqua": "#00ffff",
    "blue": "#3278ff",
    "navy": "#000080",
    "lightblue": "#b7ddff",
}


def resolve_color(color: str) -> str:
    normalized = color.lower()
    if normalized.startswith("#"):
        return normalized
    try:
        return COLORS[normalized].lower()
    except KeyError as exc:
        raise ValueError(f"Unknown color: {color}") from exc


def color_to_rgb(color: str) -> tuple[int, int, int]:
    resolved = resolve_color(color).lstrip("#")
    return (
        int(resolved[0:2], 16),
        int(resolved[2:4], 16),
        int(resolved[4:6], 16),
    )
