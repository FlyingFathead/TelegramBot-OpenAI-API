"""ChatKeke application version, loaded from the repository-root VERSION file."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "VERSION"


def read_version(version_file: Path = VERSION_FILE) -> str:
    """Return the application version from VERSION, failing loudly if invalid."""
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to read ChatKeke version from {version_file}: {exc}") from exc

    if not version:
        raise RuntimeError(f"ChatKeke VERSION file is empty: {version_file}")
    if any(char.isspace() for char in version):
        raise RuntimeError(f"ChatKeke VERSION must contain one whitespace-free version: {version_file}")

    return version


VERSION = read_version()
