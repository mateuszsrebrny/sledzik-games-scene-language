from __future__ import annotations

import argparse

from sgsl.build_glb import build_glb


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an SGSL component as a GLB asset.")
    parser.add_argument("source", help="Path to the source .sgsl file")
    parser.add_argument("--component", required=True, help="Component to instantiate and export")
    parser.add_argument("--output", "-o", help="Output GLB path")
    args = parser.parse_args()
    output = build_glb(args.source, args.component, args.output)
    print(f"{output} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
