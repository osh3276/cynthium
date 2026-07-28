# Contributing to Cynthium

Thanks for your interest. This guide covers the practical bits of getting started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project follows a **no-jerks policy**. Be respectful, constructive, and assume good faith. Harassment, personal attacks, and entitlement will not be tolerated.

## Reporting Issues

Open an issue at [github.com/osh3276/cynthium/issues](https://github.com/osh3276/cynthium/issues).

**Bugs** — include:

- Cynthium version (`cynthium --version`)
- Python version (`python --version`)
- OS and architecture
- Steps to reproduce (minimal if possible)
- Full traceback or error message
- Screenshot if applicable

**Feature requests** — describe the use case and why existing functionality doesn't cover it. A sketch of the API or UI change helps.

## Development Setup

### Prerequisites

- **Python >= 3.12**
- **C/C++ compiler** — required by `rasterio` (GDAL bindings). On Debian/Ubuntu: `build-essential`. On Fedora: `gcc-c++`. On macOS: Xcode Command Line Tools.

### Clone and install

```bash
git clone https://github.com/osh3276/cynthium.git
cd cynthium
pip install -e ".[dev]"
```

The `-e` flag installs in editable mode so changes to source files take effect immediately.

### Verify it works

```bash
cynthium
```

The application window should open. You can also run the test suite (see [Testing](#testing)).

### Dependencies

Core dependencies are listed in `pyproject.toml`. Dev dependencies (test runners, linters) should be added under `[project.optional-dependencies] dev` if not already present.

## Project Structure

```
cynthium/
├── src/
│   └── cynthium/
│       ├── app/           # Main application package
│       │   ├── engine/    # Core algorithms (pathfinding, simulation, illumination)
│       │   ├── services/  # Orchestration (autopath, simulation lifecycle)
│       │   ├── ui/        # PySide6 interface (maps, panels, dialogs)
│       │   ├── io/        # GeoTIFF reading, CSV/JSON export
│       │   ├── utils/     # Logging, helpers
│       │   ├── config/    # App configuration, site presets
│       │   ├── data/      # Pooch-based file registry
│       │   └── main.py    # Entry point
│       └── __init__.py    # Version
├── tests/                 # Test files (mirrors src layout)
├── data/                  # Downloaded raster cache (gitignored)
├── docs/                  # Sphinx documentation source
├── pyproject.toml         # Build config and dependencies
├── setup.py              # Legacy setuptools config (editable installs)
└── setup.cfg             # Metadata additions
```

## Coding Standards

### Style

- **Indentation: tabs.** No spaces. One tab per indent level.
- **Line length:** aim for ~90 characters. No hard limit, but don't abuse it.
- **Naming:** `snake_case` for functions, variables, methods. `PascalCase` for classes. `UPPER_SNAKE` for constants.
- **Imports:** standard library first, then third-party, then cynthium internal. Groups separated by a blank line.
- **Type annotations:** required for all function signatures (including `-> None`). Use `from __future__ import annotations` for forward references.
- **Docstrings:** use Google-style docstrings for public functions and classes. Internal helpers can use a single-line comment.
- **No commented-out code.** Delete it. Git history exists for a reason.

### Linters and formatting

Before submitting, run:

```bash
# Check types
mypy src/

# Lint
ruff check src/

# Format (tabs preserved)
ruff format src/ --no-cache
```

If a linter rule produces a false positive, add a `# noqa: <rule>` inline comment with a brief justification.

### Commit messages

Use conventional commits:

```
<type>: <short description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `chore`.

Keep the subject line under 72 characters. Reference issues with `#NNN`.

## Testing

Tests live in `tests/` and use `pytest`.

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_pid_speed_controller.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src/cynthium
```

When adding a feature, include tests that cover:

- The happy path
- Edge cases (empty inputs, extreme values, invalid coordinates)
- Error handling (bad files, missing data, network failures in pooch downloads)

For GUI changes, test the underlying logic (engine, services, io) separately. Direct UI testing is not required at this stage.

## Pull Request Process

1. **Open an issue** first (unless it's a tiny bugfix). Discuss the approach before writing code.
2. **Fork the repo** and create a branch from `main`. Name it descriptively: `fix/progress-dialog-hang`, `feat/waypoint-pause`.
3. **Make your changes.** Keep them focused. One PR = one logical change.
4. **Write or update tests** as needed.
5. **Run the linter and tests** locally (see sections above).
6. **Keep the changelog updated** under the `[Unreleased]` section in `CHANGELOG.md`, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
7. **Open a PR** against `main`. In the description, link the issue and summarise what changed and why.
8. **Review.** Address feedback. A maintainer will merge when everything is green.

### Before you open the PR, check

- [ ] Tests pass (`pytest`)
- [ ] Linter passes (`ruff check src/`)
- [ ] Types check (`mypy src/`)
- [ ] Changelog updated
- [ ] New dependencies added to `pyproject.toml` (not `setup.py`)
- [ ] No debug prints, commented code, or TODOs left behind

## Release Process

For maintainers:

1. Update `CHANGELOG.md` — set the version and date under the release heading.
2. Update `__version__` in `src/cynthium/__init__.py`.
3. Commit: `chore: bump version to X.Y.Z`.
4. Tag: `git tag vX.Y.Z`.
5. Push: `git push && git push --tags`.
6. Build and publish to PyPI (if applicable).
