"""Generate VersionClimber config.yaml from RepoProfile."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from coderevival.profile import RepoProfile

# Package priority tiers for selection
PRIORITY_TIERS = [
    # Tier 1: Always include
    ["python"],
    # Tier 2: Core scientific (if detected)
    ["numpy", "scipy", "pandas", "matplotlib", "seaborn"],
    # Tier 3: Web frameworks (pick one if detected)
    ["fastapi", "flask", "django", "streamlit"],
    # Tier 4: Specialized (if detected)
    ["jupyter", "notebook", "nbconvert", "h5py", "pytorch", "tensorflow"],
]

# Packages commonly available on conda-forge
CONDA_FORGE_COMMON = {
    "numpy", "scipy", "pandas", "matplotlib", "seaborn",
    "jupyter", "notebook", "nbconvert", "h5py",
    "scikit-learn", "python", "pytest", "flask", "django",
}

# Exclude from package selection and smoke tests
EXCLUDE_PACKAGES = {
    "pytest", "flake8", "black", "mypy", "pylint", "ipython",
    "autopep8", "yapf", "isort", "coverage", "tox",
}

# Maximum packages to include in config
MAX_PACKAGES = 8


def normalize_package_name(name: str) -> str:
    """Normalize package name (lowercase, hyphens)."""
    return name.lower().replace("_", "-")


def extract_version_from_spec(spec: str) -> str | None:
    """
    Extract version from a dependency spec, only for exact pins (==).
    
    Examples:
        numpy==1.21.0 → "1.21.0"
        pandas>=1.3.0 → None (not exact)
        scikit-learn → None
    """
    # Only match == for exact pins
    match = re.search(r'==\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)', spec)
    if match:
        return match.group(1)
    return None


def parse_requires_python(requires_python: str | None) -> str | None:
    """
    Extract minimum Python version from requires-python spec.
    
    Examples:
        ">=3.8" → "3.8"
        ">=3.8,<4.0" → "3.8"
        "~=3.8" → "3.8"
    """
    if not requires_python:
        return None
    match = re.search(r'[>~=]+\s*([0-9]+\.[0-9]+)', requires_python)
    if match:
        return match.group(1)
    return None


def select_packages(profile: RepoProfile) -> list[str]:
    """
    Select 5-8 core packages from all dependencies using priority heuristics.
    
    Priority:
    1. Python itself (always)
    2. Tier-based priority (scientific, web, specialized)
    3. First N packages from requirements (chronological order)
    4. Exclude test/dev tools
    5. Auto-add notebook packages if .ipynb files found
    """
    # Collect all packages from dependency files
    all_packages: set[str] = set()
    first_file_packages: list[str] = []
    
    for df in profile.python.dependency_files:
        for pkg in df.packages:
            normalized = normalize_package_name(pkg)
            all_packages.add(normalized)
            if not first_file_packages:
                first_file_packages.append(normalized)
    
    # Remove excluded packages
    all_packages -= EXCLUDE_PACKAGES
    
    # Check for notebook files
    has_ipynb_files = any(".ipynb" in marker for lang in profile.languages.detected for marker in lang.markers)
    if has_ipynb_files:
        # Auto-add notebook packages if we have .ipynb files
        all_packages.add("notebook")
        all_packages.add("nbconvert")
    
    selected: list[str] = []
    selected_set: set[str] = set()
    
    # Apply priority tiers
    for tier in PRIORITY_TIERS:
        for pkg in tier:
            if pkg in all_packages and pkg not in selected_set:
                selected.append(pkg)
                selected_set.add(pkg)
                if len(selected) >= MAX_PACKAGES:
                    return selected
    
    # Fill remaining slots with packages from first dependency file (chronological)
    for pkg in first_file_packages:
        if pkg not in selected_set and pkg not in EXCLUDE_PACKAGES:
            selected.append(pkg)
            selected_set.add(pkg)
            if len(selected) >= MAX_PACKAGES:
                return selected
    
    # Fill any remaining slots with other detected packages
    for pkg in sorted(all_packages):
        if pkg not in selected_set:
            selected.append(pkg)
            selected_set.add(pkg)
            if len(selected) >= MAX_PACKAGES:
                return selected
    
    return selected


def get_package_versions(profile: RepoProfile) -> dict[str, str | None]:
    """
    Extract pinned versions for packages from dependency files.
    
    Returns dict mapping package name → version (or None if not pinned).
    """
    versions: dict[str, str | None] = {}
    
    # Read actual dependency files to get version specs
    root = Path(profile.clone_path)
    
    for df in profile.python.dependency_files:
        dep_file = root / df.path
        if not dep_file.exists():
            continue
        
        try:
            content = dep_file.read_text(encoding="utf-8", errors="replace")
            
            if dep_file.name in ("requirements.txt", "requirements-dev.txt") or \
               dep_file.name.startswith("requirements"):
                # Parse requirements.txt style
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    
                    # Extract package name
                    pkg_match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if pkg_match:
                        pkg_name = normalize_package_name(pkg_match.group(1))
                        version = extract_version_from_spec(line)
                        if version and pkg_name not in versions:
                            versions[pkg_name] = version
            
            elif dep_file.name in ("environment.yml", "environment.yaml"):
                # Parse conda environment.yml
                in_deps = False
                for line in content.splitlines():
                    if line.strip().startswith("dependencies:"):
                        in_deps = True
                        continue
                    if in_deps and line.startswith("  - "):
                        spec = line[4:].strip()
                        pkg_match = re.match(r'^([a-zA-Z0-9_-]+)', spec)
                        if pkg_match:
                            pkg_name = normalize_package_name(pkg_match.group(1))
                            version = extract_version_from_spec(spec)
                            if version and pkg_name not in versions:
                                versions[pkg_name] = version
                    elif in_deps and not line.startswith(" "):
                        break
        
        except Exception:
            # Skip files we can't read
            continue
    
    return versions


def get_python_version(profile: RepoProfile, versions: dict[str, str | None]) -> str | None:
    """
    Determine Python version to use as starting point.
    
    Priority:
    1. CI Python version
    2. requires-python lower bound
    3. Pinned version from environment.yml
    4. Default: "3.8"
    """
    # Check CI
    if profile.python.ci_python_versions:
        return profile.python.ci_python_versions[0]
    
    # Check requires-python
    if profile.python.requires_python:
        py_ver = parse_requires_python(profile.python.requires_python)
        if py_ver:
            return py_ver
    
    # Check if pinned in versions dict
    if "python" in versions and versions["python"]:
        return versions["python"]
    
    # Default
    return "3.8"


def infer_vcs(package: str, profile: RepoProfile) -> str:
    """
    Determine vcs (conda vs pypi) for a package.
    
    Logic:
    1. If environment.yml exists → conda for common packages
    2. If package in CONDA_FORGE_COMMON → conda
    3. Otherwise → pypi
    """
    # Check if environment.yml exists
    has_conda_env = any(
        df.path in ("environment.yml", "environment.yaml")
        for df in profile.python.dependency_files
    )
    
    if has_conda_env or package in CONDA_FORGE_COMMON:
        return "conda"
    
    return "pypi"


def find_notebook_files(profile: RepoProfile) -> list[str]:
    """Find .ipynb files in the repository."""
    root = Path(profile.clone_path)
    notebooks: list[str] = []
    
    try:
        for nb in root.rglob("*.ipynb"):
            # Exclude .ipynb_checkpoints
            if ".ipynb_checkpoints" not in nb.parts:
                rel_path = nb.relative_to(root)
                notebooks.append(str(rel_path))
    except Exception:
        pass
    
    return notebooks


def generate_run_command(profile: RepoProfile, selected_packages: list[str]) -> list[str]:
    """
    Generate run: command using priority cascade.
    
    Priority:
    1. CI test command
    2. Notebook execution (if .ipynb files found)
    3. README run hints (test-related)
    4. Detected test framework
    5. Smoke import fallback
    """
    # Priority 1: CI test command
    if profile.python.ci_test_command:
        return [profile.python.ci_test_command]
    
    # Priority 2: Notebook execution (check for .ipynb in language markers)
    has_ipynb = any(".ipynb" in marker for lang in profile.languages.detected for marker in lang.markers)
    if has_ipynb:
        notebooks = find_notebook_files(profile)
        if notebooks:
            # Use first notebook found
            nb_path = notebooks[0]
            return [f"jupyter-nbconvert --ExecutePreprocessor.timeout=60 --to notebook --execute {nb_path}"]
    
    # Priority 3: README run hints
    if profile.documentation.run_hints:
        for hint in profile.documentation.run_hints:
            hint_lower = hint.lower()
            if any(kw in hint_lower for kw in ["pytest", "test", "unittest", "nose"]):
                return [hint]
    
    # Priority 4: Test framework detected
    for tf in profile.test_frameworks:
        if tf.id == "pytest":
            return ["pytest -q"]
        elif tf.id == "unittest":
            return ["python -m unittest discover"]
        elif tf.id == "nose":
            return ["nosetests"]
    
    # Priority 5: Smoke import fallback
    importable = [pkg for pkg in selected_packages if pkg not in EXCLUDE_PACKAGES and pkg != "python"]
    if importable:
        # Limit to first 5 for readability
        imports = ", ".join(importable[:5])
        return [f"python -c 'import {imports}'"]
    
    # Last resort
    return ["python --version"]


def generate_config_yaml(profile: RepoProfile) -> str:
    """
    Generate complete VersionClimber config.yaml from RepoProfile.
    
    Returns YAML string ready to write to file.
    """
    selected_packages = select_packages(profile)
    package_versions = get_package_versions(profile)
    
    # Ensure python is included
    if "python" not in selected_packages:
        selected_packages.insert(0, "python")
    
    lines: list[str] = []
    
    # Add pre: git clone if we have a repo URL
    if profile.repo_url:
        lines.extend([
            f"pre: git clone {profile.repo_url}",
            "",
        ])
    
    lines.append("packages:")
    
    # Generate package entries
    for pkg in selected_packages:
        vcs = infer_vcs(pkg, profile)
        version = package_versions.get(pkg)
        
        # Only include version if we have an exact pin (not for python or partial constraints)
        # VersionClimber will search for compatible versions when version is omitted
        include_version = (version and pkg != "python")
        
        lines.append(f"    - name      : {pkg}")
        
        # Add version only if exact pin found
        if include_version:
            lines.append(f"      version   : \"{version}\"")
        
        lines.append(f"      vcs       : {vcs}")
        
        if vcs == "conda":
            lines.append(f"      cmd       : conda install -y")
            lines.append(f"      channels  :")
            lines.append(f"        - conda-forge")
        else:
            lines.append(f"      cmd       : pip install -U")
        
        lines.append(f"      hierarchy : patch")
        
        # Python gets major supply, others get minor
        if pkg == "python":
            lines.append(f"      supply    : major")
        else:
            lines.append(f"      supply    : minor")
        
        lines.append("")  # Blank line between packages
    
    # Generate run command
    run_commands = generate_run_command(profile, selected_packages)
    lines.append("run:")
    for cmd in run_commands:
        lines.append(f"    - {cmd}")
    
    # Add post: conda env export (standard)
    lines.extend([
        "",
        "post: conda env export > environment.yml",
    ])
    
    return "\n".join(lines) + "\n"


def generate_config_to_file(profile: RepoProfile, output_path: Path | None = None) -> Path:
    """
    Generate config.yaml and write to file.
    
    Args:
        profile: RepoProfile from analysis phase
        output_path: Optional custom output path, defaults to clone_path/config.yaml
    
    Returns:
        Path to generated config.yaml
    """
    if output_path is None:
        output_path = Path(profile.clone_path) / "config.yaml"
    
    config_content = generate_config_yaml(profile)
    output_path.write_text(config_content, encoding="utf-8")
    
    return output_path
