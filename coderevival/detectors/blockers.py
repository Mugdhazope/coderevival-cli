"""Revival blockers and external services."""

from __future__ import annotations

from pathlib import Path

HEAVY_ML = {"tensorflow", "torch", "keras", "pytorch", "tensorflow-gpu"}


def detect_blockers_and_services(
    root: Path,
    all_packages: list[str],
    ci_signals: dict[str, bool],
    files: list[str],
    compose: bool,
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    services: list[str] = []

    if (root / ".dvc").is_dir() or any(f.endswith(".dvc") for f in files):
        blockers.append("dvc_data")
        services.append("dvc")

    if ci_signals.get("dvc"):
        if "dvc_data" not in blockers:
            blockers.append("dvc_data")

    if ci_signals.get("secrets"):
        blockers.append("ci_secrets")

    if ci_signals.get("aws"):
        services.append("aws")
        blockers.append("ci_secrets_aws")

    for p in all_packages:
        base = p.split("[", 1)[0]
        if base in HEAVY_ML or "tensorflow" in base or base == "keras":
            if "tensorflow_listed" not in blockers:
                blockers.append("tensorflow_listed")
            break
        if base == "torch" or base == "torchvision" or "pytorch" in base:
            if "pytorch_listed" not in blockers:
                blockers.append("pytorch_listed")
            break

    if compose:
        services.append("docker_compose")
        compose_text = ""
        for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml"):
            p = root / name
            if p.is_file():
                compose_text += p.read_text(encoding="utf-8", errors="replace").lower()
        if "postgres" in compose_text:
            services.append("postgres")
            blockers.append("database_compose")
        if "mysql" in compose_text or "mariadb" in compose_text:
            services.append("mysql")
            blockers.append("database_compose")
        if "redis" in compose_text:
            services.append("redis")

    # dedupe
    blockers = sorted(set(blockers))
    services = sorted(set(services))
    return blockers, services


def compute_readiness(
    primary_lang: str,
    blockers: list[str],
) -> tuple[str, list[str]]:
    notes: list[str] = []
    if primary_lang != "python":
        notes.append(f"Primary language is {primary_lang}; Python VersionClimber pipeline not primary.")
        return "unsupported", notes

    heavy = [b for b in blockers if b in ("tensorflow_listed", "pytorch_listed", "dvc_data", "ci_secrets_aws")]
    if heavy:
        notes.append("Heavy ML, DVC, or CI secrets suggest limited unattended revival.")
        return "limited", notes

    if blockers:
        notes.append("Minor blockers flagged; manual review recommended.")
        return "limited", notes

    notes.append("Suitable for Python dependency pipeline (Phase B next steps).")
    return "ready", notes
