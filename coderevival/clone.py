"""Clone GitHub repositories or resolve local paths."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class CloneResult:
    path: Path
    repo_url: str | None
    owner: str | None
    name: str | None
    commit_sha: str | None


_GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    re.I,
)


def parse_github_url(url: str) -> tuple[str, str] | None:
    url = url.strip().rstrip("/")
    m = _GITHUB_RE.match(url)
    if m:
        return m.group("owner"), m.group("repo").removesuffix(".git")
    parsed = urlparse(url)
    if parsed.netloc.lower() in ("github.com", "www.github.com"):
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1].removesuffix(".git")
    return None


def workspace_dir_name(owner: str, repo: str) -> str:
    return f"{owner}-{repo}"


def git_head_sha(repo_path: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def clone_github(
    url: str,
    output_dir: Path,
    depth: int = 1,
) -> CloneResult:
    parsed = parse_github_url(url)
    if not parsed:
        raise ValueError(f"Not a GitHub repository URL: {url}")
    owner, repo = parsed
    dest = output_dir / workspace_dir_name(owner, repo)
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_url = f"https://github.com/{owner}/{repo}.git"

    if dest.exists() and (dest / ".git").is_dir():
        subprocess.run(
            ["git", "-C", str(dest), "fetch", "--depth", str(depth), "origin"],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False,
            capture_output=True,
        )
    else:
        if dest.exists():
            raise FileExistsError(f"Path exists but is not a git repo: {dest}")
        cmd = ["git", "clone", "--depth", str(depth), repo_url, str(dest)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    return CloneResult(
        path=dest.resolve(),
        repo_url=f"https://github.com/{owner}/{repo}",
        owner=owner,
        name=repo,
        commit_sha=git_head_sha(dest),
    )


def resolve_local_path(path: str) -> CloneResult:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise FileNotFoundError(f"Not a directory: {p}")
    owner, name = None, None
    parsed = None
    try:
        out = subprocess.run(
            ["git", "-C", str(p), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote = out.stdout.strip()
        parsed = parse_github_url(remote)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    repo_url = None
    if parsed:
        owner, name = parsed
        repo_url = f"https://github.com/{owner}/{name}"
    return CloneResult(
        path=p,
        repo_url=repo_url,
        owner=owner,
        name=name,
        commit_sha=git_head_sha(p) if (p / ".git").exists() else None,
    )
