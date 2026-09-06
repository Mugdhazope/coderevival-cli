"""Language detection via extensions and marker files."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from coderevival.profile import LanguageEntry, LanguagesInfo

EXTENSION_LANG = {
    ".py": "python",
    ".pyi": "python",
    ".ipynb": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".sh": "shell",
}

MARKER_LANG = {
    "package.json": "javascript",
    "pnpm-lock.yaml": "javascript",
    "yarn.lock": "javascript",
    "package-lock.json": "javascript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "Gemfile": "ruby",
    "composer.json": "php",
    "mix.exs": "elixir",
}


def detect_languages(root: Path, files: list[str]) -> LanguagesInfo:
    counts: Counter[str] = Counter()
    markers: dict[str, list[str]] = {}

    for f in files:
        base = f.split("/")[-1]
        if base in MARKER_LANG:
            lang = MARKER_LANG[base]
            counts[lang] += 5
            markers.setdefault(lang, []).append(base)
        ext = Path(f).suffix
        if ext in EXTENSION_LANG:
            lang = EXTENSION_LANG[ext]
            counts[lang] += 1
            if len(markers.get(lang, [])) < 5:
                markers.setdefault(lang, []).append(f"*{ext}")

    if not counts:
        return LanguagesInfo(primary="unknown", detected=[])

    primary = counts.most_common(1)[0][0]
    detected: list[LanguageEntry] = []
    for lang, count in counts.most_common():
        if lang == primary and count >= 3:
            conf = "high"
        elif count >= 2:
            conf = "medium"
        else:
            conf = "low"
        detected.append(
            LanguageEntry(
                id=lang,
                confidence=conf,
                markers=sorted(set(markers.get(lang, [])))[:8],
            )
        )
    return LanguagesInfo(primary=primary, detected=detected)
