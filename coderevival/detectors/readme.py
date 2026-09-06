"""README and documentation signals."""

from __future__ import annotations

import re
from pathlib import Path

from coderevival.profile import DocumentationInfo

INSTALL_PATTERNS = [
    re.compile(r"pip\s+install[^\n`]{0,120}", re.I),
    re.compile(r"conda\s+install[^\n`]{0,120}", re.I),
    re.compile(r"npm\s+install[^\n`]{0,80}", re.I),
    re.compile(r"poetry\s+install[^\n`]{0,80}", re.I),
    re.compile(r"pip\s+install\s+-r\s+\S+", re.I),
]

RUN_PATTERNS = [
    re.compile(r"pytest[^\n`]{0,80}", re.I),
    re.compile(r"streamlit\s+run[^\n`]{0,80}", re.I),
    re.compile(r"python\s+\S+\.py[^\n`]{0,60}", re.I),
    re.compile(r"flask\s+run[^\n`]{0,60}", re.I),
    re.compile(r"make\s+\w+", re.I),
    re.compile(r"npm\s+(run|start)\s+\w+", re.I),
]


def _find_readmes(root: Path) -> list[Path]:
    found: list[Path] = []
    for p in sorted(root.iterdir()):
        if not p.is_file():
            continue
        upper = p.name.upper()
        if upper.startswith("README"):
            found.append(p)
    return found


def detect_documentation(root: Path) -> DocumentationInfo:
    readmes = _find_readmes(root)
    contributing = (root / "CONTRIBUTING.md").is_file() or (root / "CONTRIBUTING.rst").is_file()
    install_hints: list[str] = []
    run_hints: list[str] = []
    excerpt = ""

    texts: list[str] = []
    for rm in readmes:
        texts.append(rm.read_text(encoding="utf-8", errors="replace"))
    if contributing:
        cp = root / "CONTRIBUTING.md"
        if cp.is_file():
            texts.append(cp.read_text(encoding="utf-8", errors="replace"))

    combined = "\n".join(texts)
    if combined:
        excerpt = combined.strip().replace("\n", " ")[:200]

    for text in texts:
        for pat in INSTALL_PATTERNS:
            for m in pat.finditer(text):
                hint = m.group(0).strip()
                if hint not in install_hints and len(install_hints) < 8:
                    install_hints.append(hint)
        for pat in RUN_PATTERNS:
            for m in pat.finditer(text):
                hint = m.group(0).strip()
                if hint not in run_hints and len(run_hints) < 8:
                    run_hints.append(hint)

    return DocumentationInfo(
        readme_present=bool(readmes),
        readme_paths=[p.name for p in readmes],
        contributing_present=contributing,
        install_hints=install_hints,
        run_hints=run_hints,
        readme_excerpt=excerpt,
    )
