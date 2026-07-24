"""Validation tests for the Phase 1 project skeleton."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    "app/api",
    "app/bot",
    "app/config",
    "app/core",
    "app/dispatcher",
    "app/handlers",
    "app/models",
    "app/repositories",
    "app/schemas",
    "app/services",
    "app/utils",
    "app/workers",
    "database/migrations",
    "database/migrations/versions",
    "docs",
    "logs",
    "scripts",
    "tests/api",
    "tests/bot",
    "tests/config",
    "tests/core",
    "tests/dispatcher",
    "tests/fixtures",
    "tests/handlers",
    "tests/integration",
    "tests/repositories",
    "tests/services",
)

REQUIRED_FILES = (
    ".env.example",
    ".gitignore",
    ".python-version",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
)


def test_required_directories_exist() -> None:
    """The Phase 1 directory tree must match the documented structure."""
    missing = [
        directory
        for directory in REQUIRED_DIRECTORIES
        if not (PROJECT_ROOT / directory).is_dir()
    ]

    assert not missing, f"Missing required directories: {missing}"


def test_required_files_exist() -> None:
    """The Phase 1 root configuration files must exist."""
    missing = [
        filename
        for filename in REQUIRED_FILES
        if not (PROJECT_ROOT / filename).is_file()
    ]

    assert not missing, f"Missing required files: {missing}"


def test_python_version_is_pinned_to_312() -> None:
    """The repository must explicitly target Python 3.12."""
    configured_version = (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8")

    assert configured_version.strip() == "3.12"


def test_local_environment_file_is_ignored() -> None:
    """Local secrets must not be committed to the repository."""
    ignore_rules = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env\n" in ignore_rules
    assert "!.env.example" in ignore_rules
