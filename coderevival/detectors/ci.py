"""GitHub Actions workflow parsing."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml  # type: ignore

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _workflow_files(root: Path) -> list[Path]:
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return []
    return sorted(wf.glob("*.yml")) + sorted(wf.glob("*.yaml"))


def _clean_python_versions(versions: list[str]) -> list[str]:
    out: list[str] = []
    for v in versions:
        v = v.strip("'\" ")
        if "${{" in v or "matrix" in v.lower():
            continue
        if re.match(r"^3\.\d+(\.\d+)?$", v):
            out.append(v)
    return sorted(set(out))


def _parse_with_regex(text: str) -> tuple[list[str], str | None]:
    py_versions: list[str] = []
    for m in re.finditer(r"python-version:\s*\[?([^\]\n#]+)", text):
        chunk = m.group(1).strip()
        for part in re.split(r"[\s,]+", chunk):
            part = part.strip("'\" ")
            if re.match(r"^3\.\d+", part):
                py_versions.append(part)
    for m in re.finditer(r"python-version:\s*['\"]?([0-9.]+)", text):
        py_versions.append(m.group(1))

    test_cmd: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("pytest ") or stripped.startswith("python -m pytest"):
            test_cmd = stripped
    for m in re.finditer(r"run:\s*\|\s*\n((?:\s+.+\n)+)", text):
        block = m.group(1)
        for ln in block.splitlines():
            ln = ln.strip()
            if "pytest" in ln:
                test_cmd = ln
                break
    for m in re.finditer(r"run:\s*\n\s+([^\n]+pytest[^\n]*)", text):
        test_cmd = m.group(1).strip()

    return _clean_python_versions(py_versions), test_cmd


def _parse_with_yaml(text: str) -> tuple[list[str], str | None]:
    py_versions: list[str] = []
    test_cmds: list[str] = []
    try:
        data = yaml.safe_load(text)
    except Exception:
        return _parse_with_regex(text)
    if not isinstance(data, dict):
        return _parse_with_regex(text)

    def walk(obj):
        nonlocal py_versions, test_cmds
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "python-version":
                    if isinstance(v, list):
                        py_versions.extend(str(x) for x in v)
                    elif v:
                        py_versions.append(str(v))
                if k == "run" and isinstance(v, str):
                    if "pytest" in v or "python -m pytest" in v:
                        test_cmds.append(v.strip())
                    for line in v.splitlines():
                        line = line.strip()
                        if "pytest" in line:
                            test_cmds.append(line)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    test_cmd = test_cmds[0] if test_cmds else None
    if not py_versions:
        return _parse_with_regex(text)
    return _clean_python_versions(py_versions), test_cmd


def parse_ci(root: Path) -> tuple[list[str], str | None, list[str]]:
    """Returns (python_versions, test_command, workflow_paths)."""
    py_versions: list[str] = []
    test_cmd: str | None = None
    paths: list[str] = []
    for wf in _workflow_files(root):
        rel = wf.relative_to(root).as_posix()
        paths.append(rel)
        text = wf.read_text(encoding="utf-8", errors="replace")
        if _HAS_YAML:
            pvs, tc = _parse_with_yaml(text)
        else:
            pvs, tc = _parse_with_regex(text)
        py_versions.extend(pvs)
        if tc and not test_cmd:
            test_cmd = tc
    return _clean_python_versions(py_versions), test_cmd, paths


def scan_workflows_for_signals(root: Path) -> dict[str, bool]:
    """Secrets, AWS, DVC mentions in CI."""
    signals = {"secrets": False, "aws": False, "dvc": False}
    for wf in _workflow_files(root):
        text = wf.read_text(encoding="utf-8", errors="replace").lower()
        if "secrets." in text:
            signals["secrets"] = True
        if "aws-actions" in text or "configure-aws" in text:
            signals["aws"] = True
        if "dvc" in text:
            signals["dvc"] = True
    return signals
