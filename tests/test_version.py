from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import app_version  # noqa: E402


def test_root_version_file_is_single_source_of_truth() -> None:
    expected = (ROOT_DIR / "VERSION").read_text(encoding="utf-8").strip()
    assert expected
    assert app_version.VERSION == expected
    assert app_version.read_version() == expected


def test_read_version_rejects_empty_file(tmp_path: Path) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("\n", encoding="utf-8")

    try:
        app_version.read_version(version_file)
    except RuntimeError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty VERSION should fail")


def test_read_version_rejects_whitespace_inside_version(tmp_path: Path) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3 beta\n", encoding="utf-8")

    try:
        app_version.read_version(version_file)
    except RuntimeError as exc:
        assert "whitespace-free" in str(exc)
    else:
        raise AssertionError("VERSION containing whitespace should fail")
