"""Dependency extraction from common Python project files."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore

# Relative paths often used for requirements
REQUIREMENTS_GLOBS = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements/dev.txt",
    "requirements/base.txt",
    "requirements/production.txt",
    "requirements/test.txt",
    "environment.yml",
    "environment.yaml",
    "pyproject.toml",
    "setup.py",
)


def normalize_name(spec: str) -> str:
    spec = spec.strip().split("#", 1)[0].strip()
    if spec.startswith("-r ") or spec.startswith("-e "):
        return ""
    spec = re.split(r"[<>=!~\[]", spec, maxsplit=1)[0].strip()
    return spec.lower().replace("_", "-")


def from_requirements(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") and not line.startswith("-r"):
            continue
        name = normalize_name(line)
        if name:
            names.append(name)
    return names


def from_pyproject(path: Path) -> tuple[list[str], str | None]:
    if tomllib is None:
        return [], None
    data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    project = data.get("project", {})
    deps = project.get("dependencies", [])
    packages = [normalize_name(d) for d in deps]
    packages = [p for p in packages if p and "python-version" not in p]
    requires = project.get("requires-python")
    return packages, requires


def from_environment_yml(path: Path) -> list[str]:
    names: list[str] = []
    in_deps = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("dependencies:"):
            in_deps = True
            continue
        if in_deps:
            if line.startswith("  - "):
                names.append(normalize_name(line[4:]))
            elif not line.startswith(" "):
                break
    return [n for n in names if n]


def from_setup_py(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    names: list[str] = []
    # install_requires=[...] or install_requires = (...)
    m = re.search(r"install_requires\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if m:
        for part in re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)):
            name = normalize_name(part)
            if name:
                names.append(name)
    return names


def find_dependency_files(root: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for rel in REQUIREMENTS_GLOBS:
        p = root / rel
        if p.is_file() and p not in seen:
            seen.add(p)
            found.append(p)
    for p in sorted(root.glob("requirements*.txt")):
        if p.is_file() and p not in seen:
            seen.add(p)
            found.append(p)
    return found


def parse_dependency_file(path: Path) -> tuple[list[str], str | None]:
    """Returns (packages, requires_python if from pyproject)."""
    name = path.name.lower()
    rel = path.relative_to(path.parents[len(path.parents) - 1]) if path.is_absolute() else path.name
    if name == "pyproject.toml":
        return from_pyproject(path)
    if name in ("environment.yml", "environment.yaml"):
        return from_environment_yml(path), None
    if name == "setup.py":
        return from_setup_py(path), None
    if "requirements" in name or name.endswith(".txt"):
        return from_requirements(path), None
    return [], None


def collect(root: Path) -> tuple[list[tuple[str, list[str]]], str | None]:
    """
    Scan repo for dependency files.
    Returns ([(relative_path, packages), ...], requires_python).
    """
    root = root.resolve()
    entries: list[tuple[str, list[str]]] = []
    requires_python: str | None = None
    for path in find_dependency_files(root):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        if path.name == "pyproject.toml":
            pkgs, req = from_pyproject(path)
            if req:
                requires_python = req
        else:
            pkgs, _ = parse_dependency_file(path)
        if pkgs or path.name in ("pyproject.toml", "requirements.txt"):
            entries.append((rel, pkgs))
    return entries, requires_python


def dedupe_packages(packages: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in packages:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out
