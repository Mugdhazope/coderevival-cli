"""Test framework detection."""

from __future__ import annotations

from coderevival.profile import TestFrameworkEntry


def detect_test_frameworks(files: list[str]) -> list[TestFrameworkEntry]:
    found: list[TestFrameworkEntry] = []
    basenames = {f.split("/")[-1] for f in files}

    if "pytest.ini" in basenames or "conftest.py" in basenames:
        markers = [f for f in files if f.endswith("pytest.ini") or f.endswith("conftest.py")][:5]
        found.append(TestFrameworkEntry(id="pytest", markers=markers or ["pytest.ini/conftest.py"]))
    elif any("/tests/" in f or f.startswith("tests/") for f in files):
        found.append(TestFrameworkEntry(id="pytest", markers=["tests/"]))
    elif any(f.startswith("test_") and f.endswith(".py") for f in files):
        found.append(TestFrameworkEntry(id="pytest", markers=["test_*.py"]))

    if "tox.ini" in basenames:
        found.append(TestFrameworkEntry(id="tox", markers=["tox.ini"]))
    if "noxfile.py" in basenames:
        found.append(TestFrameworkEntry(id="nox", markers=["noxfile.py"]))
    if any("unittest" in f for f in files if f.endswith(".py")):
        found.append(TestFrameworkEntry(id="unittest", markers=["unittest imports"]))

    # JavaScript
    if "jest.config.js" in basenames or "jest.config.ts" in basenames:
        found.append(TestFrameworkEntry(id="jest", markers=["jest.config.*"]))
    if "package.json" in basenames:
        found.append(TestFrameworkEntry(id="npm_test", markers=["package.json scripts.test"]))

    return found
