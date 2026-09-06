"""CLI for CodeRevival."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coderevival.analyze import analyze_repository, write_outputs
from coderevival.clone import clone_github, resolve_local_path
from coderevival.config_generator import generate_config_to_file
from coderevival.profile import RepoProfile


def _default_workspace() -> Path:
    return Path(__file__).resolve().parent.parent / "workspace"


def cmd_analyze(args: argparse.Namespace) -> int:
    target = args.target.strip()
    workspace = Path(args.output_dir)

    if target.startswith("http://") or target.startswith("https://") or "github.com" in target:
        result = clone_github(target, workspace, depth=args.depth)
        clone_path = result.path
        repo_url = result.repo_url
        commit_sha = result.commit_sha
    else:
        result = resolve_local_path(target)
        clone_path = result.path
        repo_url = result.repo_url
        commit_sha = result.commit_sha

    profile = analyze_repository(clone_path, repo_url=repo_url, commit_sha=commit_sha)
    json_path, md_path = write_outputs(profile, json_only=args.json_only)

    print(f"Wrote {json_path}")
    if md_path:
        print(f"Wrote {md_path}")
    print(f"Primary language: {profile.languages.primary}")
    print(f"Python pipeline readiness: {profile.revival_readiness.python_pipeline}")
    if profile.blockers:
        print(f"Blockers: {', '.join(profile.blockers)}")
    
    # Generate config.yaml if requested
    if args.generate_config:
        config_path = generate_config_to_file(profile)
        print(f"Wrote {config_path}")
    
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate config.yaml from existing repo_profile.json"""
    profile_path = Path(args.profile_path)
    
    if not profile_path.exists():
        print(f"Error: {profile_path} not found", file=sys.stderr)
        return 1
    
    try:
        profile = RepoProfile.from_json(profile_path)
    except Exception as e:
        print(f"Error reading profile: {e}", file=sys.stderr)
        return 1
    
    output_path = Path(args.output) if args.output else None
    config_path = generate_config_to_file(profile, output_path)
    
    print(f"Generated: {config_path}")
    print(f"Selected {len([line for line in config_path.read_text().splitlines() if '- name' in line])} packages")
    
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coderevival", description="CodeRevival repository tools")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Phase 1: clone or scan repo and emit RepoProfile")
    analyze_p.add_argument(
        "target",
        help="GitHub URL or local path to repository",
    )
    analyze_p.add_argument(
        "--output-dir",
        default=str(_default_workspace()),
        help="Directory for git clones (default: coderevival/workspace)",
    )
    analyze_p.add_argument(
        "--depth",
        type=int,
        default=1,
        help="Git clone depth (default: 1)",
    )
    analyze_p.add_argument(
        "--json-only",
        action="store_true",
        help="Write repo_profile.json only",
    )
    analyze_p.add_argument(
        "--generate-config",
        action="store_true",
        help="Also generate config.yaml for VersionClimber",
    )
    analyze_p.set_defaults(func=cmd_analyze)

    # Generate subcommand
    generate_p = sub.add_parser("generate", help="Generate config.yaml from repo_profile.json")
    generate_p.add_argument(
        "profile_path",
        help="Path to repo_profile.json",
    )
    generate_p.add_argument(
        "--output",
        "-o",
        help="Output path for config.yaml (default: same dir as profile)",
    )
    generate_p.set_defaults(func=cmd_generate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
