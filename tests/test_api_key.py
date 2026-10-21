from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from api_key import (  # noqa: E402
    APIKeyConfigurationError,
    OpenAICredentials,
    api_key_fingerprint,
    build_openai_headers,
    coerce_openai_credentials,
    load_openai_credentials,
)


def _write_config(path: Path, prefer_env: bool) -> None:
    path.write_text(
        "[DEFAULT]\nPreferEnvForAPIKey = "
        + ("True" if prefer_env else "False")
        + "\n",
        encoding="utf-8",
    )


def test_environment_key_is_preferred(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    token = tmp_path / "api_token.txt"
    _write_config(config, True)
    token.write_text("sk-file-key", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-project-key  ")

    credentials = load_openai_credentials(config, token)

    assert credentials.api_key == "sk-project-key"
    assert credentials.source == "OPENAI_API_KEY"


def test_file_fallback_warns(tmp_path: Path, monkeypatch, caplog) -> None:
    config = tmp_path / "config.ini"
    token = tmp_path / "api_token.txt"
    _write_config(config, True)
    token.write_text("sk-file-key\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with caplog.at_level(logging.WARNING):
        credentials = load_openai_credentials(config, token)

    assert credentials.api_key == "sk-file-key"
    assert "falling back" in caplog.text
    assert "legacy key" in caplog.text


def test_malformed_preferred_key_does_not_fall_back(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    token = tmp_path / "api_token.txt"
    _write_config(config, True)
    token.write_text("sk-old-file-key", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-bad key")

    with pytest.raises(APIKeyConfigurationError, match="contains whitespace"):
        load_openai_credentials(config, token)


def test_placeholder_is_rejected(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.ini"
    _write_config(config, True)
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key")

    with pytest.raises(APIKeyConfigurationError, match="placeholder"):
        load_openai_credentials(config, tmp_path / "missing.txt")


def test_headers_include_optional_explicit_routing() -> None:
    credentials = OpenAICredentials(
        api_key="sk-test",
        source="test",
        organization="org_test",
        project="proj_test",
    )

    assert credentials.headers() == {
        "Authorization": "Bearer sk-test",
        "Content-Type": "application/json",
        "OpenAI-Organization": "org_test",
        "OpenAI-Project": "proj_test",
    }
    assert credentials.sdk_kwargs() == {
        "api_key": "sk-test",
        "organization": "org_test",
        "default_headers": {"OpenAI-Project": "proj_test"},
    }


def test_bot_credentials_are_reused() -> None:
    credentials = OpenAICredentials("sk-test", "test")
    bot = type("Bot", (), {"openai_credentials": credentials})()

    assert coerce_openai_credentials(bot) is credentials
    assert build_openai_headers(bot)["Authorization"] == "Bearer sk-test"


def test_logs_fingerprint_not_secret(tmp_path: Path, monkeypatch, caplog) -> None:
    config = tmp_path / "config.ini"
    _write_config(config, True)
    secret = "sk-this-must-not-appear-in-logs"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    with caplog.at_level(logging.INFO):
        credentials = load_openai_credentials(config, tmp_path / "missing.txt")

    assert secret not in caplog.text
    assert credentials.fingerprint in caplog.text
    assert credentials.fingerprint == api_key_fingerprint(secret)
