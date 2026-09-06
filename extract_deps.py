#!/usr/bin/env python3
"""Extract dependency names from a repository (CLI wrapper)."""

from __future__ import annotations

import sys
from pathlib import Path

from coderevival.deps import collect, dedupe_packages


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    entries, requires = collect(root)
    if not entries:
        print("No dependency files found.", file=sys.stderr)
        sys.exit(1)
    found: list[str] = []
    for path, pkgs in entries:
        print(f"# from {path}: {', '.join(pkgs)}")
        found.extend(pkgs)
    if requires:
        print(f"# requires-python: {requires}")
    unique = dedupe_packages(found)
    print("\n# suggested package list (add priority order + ask user):")
    for p in unique:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
