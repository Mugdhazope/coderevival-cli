# CodeRevival

Autonomous repository revival tool for Python projects. Automatically analyzes GitHub repositories and generates VersionClimber configurations to find working dependency combinations.

## Installation

```bash
pip install -e .
```

## Quick Start

### 1. Analyze a Repository

```bash
python -m coderevival analyze <github-url>
```

**Output:**
- `repo_profile.json` - Machine-readable analysis
- `PHASE1_SUMMARY.md` - Human-readable summary

### 2. Generate VersionClimber Config

```bash
# Option 1: Generate from existing profile
python -m coderevival generate repo_profile.json

# Option 2: One-shot (analyze + generate)
python -m coderevival analyze <github-url> --generate-config
```

**Output:**
- `config.yaml` - Ready for VersionClimber

### 3. Run VersionClimber

```bash
vclimb --conf config.yaml -v  # Quick version check
vclimb --conf config.yaml     # Full search
```

## Features

### Smart Repository Analysis
- **Language detection**: Primary language and confidence markers
- **Dependency extraction**: From requirements.txt, pyproject.toml, environment.yml, setup.py
- **CI parsing**: Test commands and Python versions from GitHub Actions workflows
- **Test framework detection**: pytest, unittest, nose, etc.
- **Blocker identification**: DVC, secrets, heavy ML dependencies

### Intelligent Config Generation
- **Package selection**: Priority-based heuristics (scientific → web → specialized)
- **Version discovery**: Extracts pinned versions from dependency files
- **VCS inference**: Automatically chooses conda vs pypi
- **Run command cascade**: CI → notebook → test framework → smoke import
- **Notebook auto-detection**: Adds notebook packages and execution commands

## CLI Commands

### `analyze`

Analyze a GitHub repository or local path.

```bash
python -m coderevival analyze <url|path> [options]

Options:
  --output-dir DIR        Output directory (default: workspace/)
  --depth N               Git clone depth (default: 1)
  --json-only             Skip PHASE1_SUMMARY.md generation
  --generate-config       Also generate config.yaml
```

### `generate`

Generate VersionClimber config from repo_profile.json.

```bash
python -m coderevival generate <profile_path> [options]

Options:
  -o, --output PATH       Output path for config.yaml
```

## Examples

### Example 1: Jupyter Notebook Project

```bash
python -m coderevival analyze https://github.com/pradal/ligo-binder --generate-config
```

**Generated config:**
- 8 packages: python, numpy, scipy, matplotlib, seaborn, notebook, nbconvert, h5py
- All from conda-forge
- Run command: `jupyter-nbconvert --execute index.ipynb`

### Example 2: Web Application

```bash
python -m coderevival analyze https://github.com/streamlit/streamlit-hello --generate-config
```

**Generated config:**
- 6 packages: python, numpy, pandas, streamlit, altair, pydeck
- Mix of conda (numpy, pandas) and pypi (streamlit, altair, pydeck)
- Run command: smoke import test

### Example 3: ML Project with Tests

```bash
python -m coderevival analyze https://github.com/user/ml-project --generate-config
```

**Generated config:**
- Packages with exact version pins from requirements.txt
- Run command from CI: `pytest src/tests -vv`
- Blockers flagged: DVC data requirements

## Architecture

### Phase 1: Repository Analysis
- Clone repository
- Detect languages, package managers, build systems
- Extract dependencies from multiple sources
- Parse CI workflows for test commands
- Identify blockers and external services

### Phase 2: Config Generation
- Select core packages (cap at 8)
- Infer VCS (conda vs pypi) per package
- Extract version pins (only exact ==)
- Generate run command using cascade logic
- Output VersionClimber-compatible YAML

### Phase 3: VersionClimber Integration
- Pass config to VersionClimber
- Run version discovery (`vclimb -v`)
- Execute full search for working environment
- Export environment on success

## Package Selection Logic

**Priority Tiers:**
1. Python (always included)
2. Core scientific: numpy, scipy, pandas, matplotlib, seaborn
3. Web frameworks: fastapi, flask, django, streamlit
4. Specialized: jupyter, notebook, nbconvert, h5py, pytorch, tensorflow

**Exclusions:** pytest, flake8, black, mypy, pylint (dev/test tools)

**Special Cases:**
- Auto-adds notebook packages when `.ipynb` files detected
- Caps at 8 packages for tractable search space

## Run Command Automation

**Priority Cascade:**
1. CI test command (from `.github/workflows/*.yml`)
2. Notebook execution (if `.ipynb` files found)
3. README run hints (test-related commands)
4. Detected test framework (pytest, unittest, nose)
5. Smoke import fallback

## Version Field Strategy

- **Exact pins (==)**: Included in config
- **Partial constraints (>=, ~=)**: Omitted (let VersionClimber search)
- **No version**: VersionClimber searches from latest

This prevents errors from non-existent version strings.

## Development

### Project Structure

```
coderevival/
├── coderevival/              # Main package
│   ├── __init__.py
│   ├── __main__.py
│   ├── analyze.py            # Phase 1 orchestration
│   ├── cli.py                # Command-line interface
│   ├── clone.py              # Git cloning logic
│   ├── config_generator.py   # Config YAML generation
│   ├── deps.py               # Dependency extraction
│   ├── profile.py            # RepoProfile data structures
│   ├── walk.py               # File tree walking
│   └── detectors/            # Detection modules
│       ├── languages.py
│       ├── package_managers.py
│       ├── build_systems.py
│       ├── tests.py
│       ├── ci.py
│       ├── readme.py
│       ├── runtime.py
│       └── blockers.py
├── pyproject.toml            # Package configuration
├── extract_deps.py           # Standalone dep extraction
├── tests/                    # Test repositories
└── README.md
```

### Running Tests

```bash
# Test on example repositories
python -m coderevival analyze https://github.com/pradal/ligo-binder --generate-config
python -m coderevival analyze https://github.com/streamlit/streamlit-hello --generate-config
```

## Requirements

- Python 3.8+
- PyYAML (optional, for environment.yml parsing)
- VersionClimber (for running generated configs)

## License

MIT

## Contributing

Contributions welcome! This project is under active development.

## Related Tools

- **VersionClimber**: Smart dependency version search tool
- **pip-tools**: Python dependency management
- **conda/mamba**: Package and environment management
