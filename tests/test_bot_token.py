from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import bot_token  # noqa: E402


def _write_config(path: Path, *, prefer_env: bool, allow_fallback: bool = True) -> None:
    path.write_text(
        "[DEFAULT]\n"
        f"PreferEnvForBotToken = {'True' if prefer_env else 'False'}\n"
        f"AllowBotTokenFallback = {'True' if allow_fallback else 'False'}\n"
        "AskForTokenIfNotFound = False\n",
        encoding="utf-8",
    )


def _patch_paths(monkeypatch, config: Path, token_file: Path) -> None:
    monkeypatch.setattr(bot_token, "CONFIG_PATH", config)
    monkeypatch.setattr(bot_token, "TOKEN_FILE_PATH", token_file)
    monkeypatch.setattr(bot_token, "is_running_in_docker", lambda: False)
    monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)


def test_file_override_wins_when_prefer_env_is_false(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    token_file = tmp_path / "bot_token.txt"
    _write_config(config, prefer_env=False)
    token_file.write_text("111111:file-token", encoding="utf-8")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "222222:env-token")
    _patch_paths(monkeypatch, config, token_file)

    assert bot_token.get_bot_token() == "111111:file-token"


def test_environment_wins_when_prefer_env_is_true(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    token_file = tmp_path / "bot_token.txt"
    _write_config(config, prefer_env=True)
    token_file.write_text("111111:file-token", encoding="utf-8")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "222222:env-token")
    _patch_paths(monkeypatch, config, token_file)

    assert bot_token.get_bot_token() == "222222:env-token"


def test_file_override_can_disable_environment_fallback(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    token_file = tmp_path / "bot_token.txt"
    _write_config(config, prefer_env=False, allow_fallback=False)
    token_file.write_text("111111:file-token", encoding="utf-8")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "222222:env-token")
    _patch_paths(monkeypatch, config, token_file)

    assert bot_token.get_bot_token() == "111111:file-token"
