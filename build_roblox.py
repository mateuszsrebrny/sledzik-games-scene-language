from __future__ import annotations

import argparse

from sgsl.build_roblox import build_roblox


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Roblox Lua from an SGSL scene.")
    parser.add_argument("source", help="Path to the source .sgsl file")
    parser.add_argument("--output", "-o", help="Output Lua path")
    parser.add_argument(
        "--module",
        "--rojo-module",
        action="store_true",
        help="Generate a reusable ModuleScript function instead of a standalone workspace script",
    )
    parser.add_argument(
        "--builder-require",
        default="game.ReplicatedStorage.SceneLanguagePrimitives",
        help="Lua expression used by module mode to require the Builder module",
    )
    args = parser.parse_args()

    mode = "module" if args.module else "standalone"
    output_path = build_roblox(
        args.source,
        args.output,
        mode=mode,
        builder_require=args.builder_require,
    )
    print(f"{output_path} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
