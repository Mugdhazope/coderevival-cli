"""Build system detection."""

from __future__ import annotations

from coderevival.profile import BuildSystemEntry

BUILD_MARKERS: dict[str, list[str]] = {
    "make": ["Makefile", "makefile", "GNUmakefile"],
    "cmake": ["CMakeLists.txt"],
    "meson": ["meson.build"],
    "bazel": ["WORKSPACE", "WORKSPACE.bazel", "MODULE.bazel"],
    "setuptools": ["setup.py", "setup.cfg"],
    "setuptools_pep517": ["pyproject.toml"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts"],
    "cargo": ["Cargo.toml"],
    "go": ["go.mod"],
    "npm_scripts": ["package.json"],
    "autotools": ["configure.ac", "configure.in", "Makefile.am"],
}


def detect_build_systems(files: list[str]) -> list[BuildSystemEntry]:
    basenames: dict[str, list[str]] = {}
    for f in files:
        base = f.split("/")[-1]
        basenames.setdefault(base, []).append(f)

    found: list[BuildSystemEntry] = []
    for build_id, names in BUILD_MARKERS.items():
        matched: list[str] = []
        for name in names:
            if name in basenames:
                matched.extend(basenames[name][:2])
        if matched:
            found.append(BuildSystemEntry(id=build_id, files=sorted(set(matched))[:5]))
    return found
