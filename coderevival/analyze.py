"""Orchestrate Phase 1 repository analysis."""

from __future__ import annotations

from pathlib import Path

from coderevival.deps import collect
from coderevival.detectors.blockers import compute_readiness, detect_blockers_and_services
from coderevival.detectors.build_systems import detect_build_systems
from coderevival.detectors.ci import parse_ci, scan_workflows_for_signals
from coderevival.detectors.languages import detect_languages
from coderevival.detectors.package_managers import detect_package_managers
from coderevival.detectors.readme import detect_documentation
from coderevival.detectors.runtime import detect_runtime
from coderevival.detectors.tests import detect_test_frameworks
from coderevival.profile import (
    DependencyFileEntry,
    PythonInfo,
    RepoProfile,
    RevivalReadiness,
    write_phase1_summary,
)
from coderevival.walk import list_files


def analyze_repository(
    clone_path: Path,
    repo_url: str | None = None,
    commit_sha: str | None = None,
) -> RepoProfile:
    root = clone_path.resolve()
    files = list_files(root)

    documentation = detect_documentation(root)
    languages = detect_languages(root, files)
    package_managers = detect_package_managers(files)
    build_systems = detect_build_systems(files)
    test_frameworks = detect_test_frameworks(files)
    runtime = detect_runtime(root, files)

    dep_entries, requires_python = collect(root)
    python_info = PythonInfo(
        dependency_files=[
            DependencyFileEntry(path=path, packages=pkgs) for path, pkgs in dep_entries
        ],
        requires_python=requires_python,
    )

    ci_py, ci_test, _wf_paths = parse_ci(root)
    python_info.ci_python_versions = ci_py
    python_info.ci_test_command = ci_test

    all_packages: list[str] = []
    for df in python_info.dependency_files:
        all_packages.extend(df.packages)

    ci_signals = scan_workflows_for_signals(root)
    blockers, external = detect_blockers_and_services(
        root, all_packages, ci_signals, files, runtime.compose
    )

    readiness_status, readiness_notes = compute_readiness(languages.primary, blockers)

    profile = RepoProfile(
        repo_url=repo_url,
        clone_path=str(root),
        commit_sha=commit_sha,
        analyzed_at=RepoProfile.now_iso(),
        documentation=documentation,
        languages=languages,
        package_managers=package_managers,
        build_systems=build_systems,
        test_frameworks=test_frameworks,
        python=python_info,
        runtime_hints=runtime,
        external_services=external,
        blockers=blockers,
        revival_readiness=RevivalReadiness(
            python_pipeline=readiness_status,
            notes=readiness_notes,
        ),
    )
    return profile


def write_outputs(profile: RepoProfile, json_only: bool = False) -> tuple[Path, Path | None]:
    out_dir = Path(profile.clone_path)
    json_path = out_dir / "repo_profile.json"
    profile.write_json(json_path)
    md_path = None
    if not json_only:
        md_path = out_dir / "PHASE1_SUMMARY.md"
        write_phase1_summary(profile, md_path)
    return json_path, md_path
