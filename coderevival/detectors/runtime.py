"""Runtime environment hints (Docker, devcontainer, compose)."""

from __future__ import annotations

from pathlib import Path

from coderevival.profile import RuntimeHints


def detect_runtime(root: Path, files: list[str]) -> RuntimeHints:
    docker_files = sorted(
        f for f in files if f.split("/")[-1].startswith("Dockerfile") or f == "Dockerfile"
    )
    compose = any(
        f.split("/")[-1] in ("docker-compose.yml", "docker-compose.yaml", "compose.yml")
        for f in files
    )
    devcontainer = (root / ".devcontainer" / "devcontainer.json").is_file()
    return RuntimeHints(
        docker=docker_files[:5],
        devcontainer=devcontainer,
        compose=compose,
    )
