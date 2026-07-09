from __future__ import annotations

import sys

from sgsl.build_roblox import build_roblox


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python build_roblox.py <scene.sgsl>")
        return 1

    output_path = build_roblox(sys.argv[1])
    print(f"{output_path} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
