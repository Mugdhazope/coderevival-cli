"""RepoProfile schema and serialization."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LanguageEntry:
    id: str
    confidence: str
    markers: list[str]


@dataclass
class LanguagesInfo:
    primary: str
    detected: list[LanguageEntry] = field(default_factory=list)


@dataclass
class PackageManagerEntry:
    id: str
    files: list[str]


@dataclass
class BuildSystemEntry:
    id: str
    files: list[str]


@dataclass
class TestFrameworkEntry:
    id: str
    markers: list[str]


@dataclass
class DocumentationInfo:
    readme_present: bool = False
    readme_paths: list[str] = field(default_factory=list)
    contributing_present: bool = False
    install_hints: list[str] = field(default_factory=list)
    run_hints: list[str] = field(default_factory=list)
    readme_excerpt: str = ""


@dataclass
class DependencyFileEntry:
    path: str
    packages: list[str]


@dataclass
class PythonInfo:
    dependency_files: list[DependencyFileEntry] = field(default_factory=list)
    requires_python: str | None = None
    ci_python_versions: list[str] = field(default_factory=list)
    ci_test_command: str | None = None


@dataclass
class RuntimeHints:
    docker: list[str] = field(default_factory=list)
    devcontainer: bool = False
    compose: bool = False


@dataclass
class RevivalReadiness:
    python_pipeline: str = "unsupported"
    notes: list[str] = field(default_factory=list)


@dataclass
class RepoProfile:
    repo_url: str | None
    clone_path: str
    commit_sha: str | None
    analyzed_at: str
    documentation: DocumentationInfo = field(default_factory=DocumentationInfo)
    languages: LanguagesInfo = field(default_factory=lambda: LanguagesInfo(primary="unknown"))
    package_managers: list[PackageManagerEntry] = field(default_factory=list)
    build_systems: list[BuildSystemEntry] = field(default_factory=list)
    test_frameworks: list[TestFrameworkEntry] = field(default_factory=list)
    python: PythonInfo = field(default_factory=PythonInfo)
    runtime_hints: RuntimeHints = field(default_factory=RuntimeHints)
    external_services: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    revival_readiness: RevivalReadiness = field(default_factory=RevivalReadiness)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_to_dict(self)

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> RepoProfile:
        """Load RepoProfile from JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoProfile:
        """Reconstruct RepoProfile from dictionary."""
        # Convert nested dictionaries to dataclasses
        if "documentation" in data:
            data["documentation"] = DocumentationInfo(**data["documentation"])
        
        if "languages" in data:
            lang_data = data["languages"]
            if "detected" in lang_data:
                lang_data["detected"] = [
                    LanguageEntry(**entry) for entry in lang_data["detected"]
                ]
            data["languages"] = LanguagesInfo(**lang_data)
        
        if "package_managers" in data:
            data["package_managers"] = [
                PackageManagerEntry(**pm) for pm in data["package_managers"]
            ]
        
        if "build_systems" in data:
            data["build_systems"] = [
                BuildSystemEntry(**bs) for bs in data["build_systems"]
            ]
        
        if "test_frameworks" in data:
            data["test_frameworks"] = [
                TestFrameworkEntry(**tf) for tf in data["test_frameworks"]
            ]
        
        if "python" in data:
            py_data = data["python"]
            if "dependency_files" in py_data:
                py_data["dependency_files"] = [
                    DependencyFileEntry(**df) for df in py_data["dependency_files"]
                ]
            data["python"] = PythonInfo(**py_data)
        
        if "runtime_hints" in data:
            data["runtime_hints"] = RuntimeHints(**data["runtime_hints"])
        
        if "revival_readiness" in data:
            data["revival_readiness"] = RevivalReadiness(**data["revival_readiness"])
        
        return cls(**data)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    return obj


def write_phase1_summary(profile: RepoProfile, path: Path) -> None:
    """Human-readable summary for meetings."""
    lines = [
        "# Phase 1 — Repository analysis summary",
        "",
        f"- **Analyzed at:** {profile.analyzed_at}",
        f"- **Repo URL:** {profile.repo_url or '(local path only)'}",
        f"- **Clone path:** {profile.clone_path}",
        f"- **Commit:** {profile.commit_sha or 'unknown'}",
        "",
        "## Languages",
        f"- **Primary:** {profile.languages.primary}",
    ]
    for lang in profile.languages.detected:
        lines.append(f"- {lang.id} ({lang.confidence}): {', '.join(lang.markers[:5])}")
    lines.extend(["", "## Package managers"])
    for pm in profile.package_managers:
        lines.append(f"- **{pm.id}:** {', '.join(pm.files)}")
    lines.extend(["", "## Build systems"])
    if profile.build_systems:
        for bs in profile.build_systems:
            lines.append(f"- **{bs.id}:** {', '.join(bs.files)}")
    else:
        lines.append("- (none detected)")
    lines.extend(["", "## Tests"])
    if profile.test_frameworks:
        for tf in profile.test_frameworks:
            lines.append(f"- **{tf.id}:** {', '.join(tf.markers)}")
    else:
        lines.append("- (none detected)")
    lines.extend(["", "## Python"])
    if profile.python.requires_python:
        lines.append(f"- **requires-python:** {profile.python.requires_python}")
    if profile.python.ci_python_versions:
        lines.append(f"- **CI Python:** {', '.join(profile.python.ci_python_versions)}")
    if profile.python.ci_test_command:
        lines.append(f"- **CI test command:** `{profile.python.ci_test_command}`")
    for df in profile.python.dependency_files:
        pkg_preview = ", ".join(df.packages[:8])
        if len(df.packages) > 8:
            pkg_preview += f", … ({len(df.packages)} total)"
        lines.append(f"- **{df.path}:** {pkg_preview or '(empty)'}")
    lines.extend(["", "## Documentation hints"])
    if profile.documentation.readme_paths:
        lines.append(f"- README: {', '.join(profile.documentation.readme_paths)}")
    if profile.documentation.install_hints:
        lines.append("- **Install hints:**")
        for h in profile.documentation.install_hints[:5]:
            lines.append(f"  - `{h}`")
    if profile.documentation.run_hints:
        lines.append("- **Run hints:**")
        for h in profile.documentation.run_hints[:5]:
            lines.append(f"  - `{h}`")
    lines.extend(["", "## Runtime"])
    if profile.runtime_hints.docker:
        lines.append(f"- Docker: {', '.join(profile.runtime_hints.docker)}")
    lines.append(f"- Dev container: {profile.runtime_hints.devcontainer}")
    lines.append(f"- Docker Compose: {profile.runtime_hints.compose}")
    if profile.external_services:
        lines.extend(["", "## External services (inferred)", ""])
        lines.append(", ".join(profile.external_services))
    lines.extend(["", "## Blockers", ""])
    if profile.blockers:
        for b in profile.blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- (none flagged)")
    lines.extend(
        [
            "",
            "## Revival readiness (Python pipeline)",
            f"- **Status:** {profile.revival_readiness.python_pipeline}",
        ]
    )
    for note in profile.revival_readiness.notes:
        lines.append(f"- {note}")
    if profile.documentation.readme_excerpt:
        lines.extend(["", "## README excerpt", "", profile.documentation.readme_excerpt])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
