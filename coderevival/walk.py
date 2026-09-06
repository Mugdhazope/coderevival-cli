"""Walk repository tree and collect relative file paths."""

from __future__ import annotations

from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
}


def list_files(root: Path, max_files: int = 15000) -> list[str]:
    """Return repo-relative posix paths."""
    root = root.resolve()
    out: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        out.append(path.relative_to(root).as_posix())
        if len(out) >= max_files:
            break
    return out


def has_path(files: list[str], pattern: str) -> bool:
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/"):
        prefix = pattern
        return any(f.startswith(prefix) for f in files)
    return pattern in files or any(f.endswith("/" + pattern) for f in files)


def paths_matching(files: list[str], suffix: str) -> list[str]:
    return sorted(f for f in files if f.endswith(suffix) or suffix in f)
