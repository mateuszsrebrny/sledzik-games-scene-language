from __future__ import annotations

import sys

from sgsl.build_preview import build_preview


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python build_preview.py <scene.sgsl>")
        return 1

    output_path = build_preview(sys.argv[1])
    print(f"{output_path} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
