"""Package manager detection."""

from __future__ import annotations

from coderevival.profile import PackageManagerEntry

PM_FILES: dict[str, list[str]] = {
    "pip": [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements/base.txt",
        "setup.py",
    ],
    "poetry": ["poetry.lock"],
    "pipenv": ["Pipfile", "Pipfile.lock"],
    "conda": ["environment.yml", "environment.yaml", "conda.yml"],
    "npm": ["package.json"],
    "yarn": ["yarn.lock"],
    "pnpm": ["pnpm-lock.yaml"],
    "cargo": ["Cargo.toml"],
    "go_mod": ["go.mod"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts"],
    "bundler": ["Gemfile"],
    "composer": ["composer.json"],
    "hex": ["mix.exs"],
}


def detect_package_managers(files: list[str]) -> list[PackageManagerEntry]:
    file_set = set(files)
    # also match basename at any depth
    basenames: dict[str, list[str]] = {}
    for f in files:
        base = f.split("/")[-1]
        basenames.setdefault(base, []).append(f)

    found: list[PackageManagerEntry] = []
    for pm_id, names in PM_FILES.items():
        matched: list[str] = []
        for name in names:
            if name in file_set:
                matched.append(name)
            elif name in basenames:
                matched.extend(basenames[name][:3])
        if pm_id == "pip":
            for f in files:
                if "requirements" in f and f.endswith(".txt") and f not in matched:
                    matched.append(f)
            if "pyproject.toml" in file_set or "pyproject.toml" in basenames:
                matched.append("pyproject.toml")
        if matched:
            found.append(PackageManagerEntry(id=pm_id, files=sorted(set(matched))[:10]))
    return found
