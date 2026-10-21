# api_key.py
# Centralized OpenAI credential loading and request/client configuration.

from __future__ import annotations

import configparser
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config_paths import API_TOKEN_PATH, CONFIG_PATH


class APIKeyConfigurationError(RuntimeError):
    """Raised when no valid OpenAI API credential can be resolved."""


_PLACEHOLDER_VALUES = {
    "changeme",
    "replace-me",
    "replace_me",
    "your-api-key",
    "your_api_key",
    "your-openai-api-key",
    "your_openai_api_key",
}


def api_key_fingerprint(api_key: str) -> str:
    """Return a short one-way fingerprint suitable for safe diagnostics."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalise_api_key(raw_value: Optional[str], source: str) -> Optional[str]:
    if raw_value is None:
        return None

    api_key = raw_value.strip()
    if not api_key:
        return None

    if any(character.isspace() for character in api_key):
        raise APIKeyConfigurationError(
            f"The OpenAI API key loaded from {source} contains whitespace. "
            "Paste it as one uninterrupted line."
        )

    if api_key.lower() in _PLACEHOLDER_VALUES:
        raise APIKeyConfigurationError(
            f"The OpenAI API key loaded from {source} is still a placeholder."
        )

    # Do not hard-code current key prefixes as a permanent contract. Warn only.
    if not api_key.startswith("sk-"):
        logging.warning(
            "The OpenAI API key loaded from %s does not use the currently "
            "expected 'sk-' prefix. Confirm that the full secret was copied.",
            source,
        )

    return api_key


@dataclass(frozen=True)
class OpenAICredentials:
    """Resolved OpenAI credential and optional explicit routing overrides."""

    api_key: str
    source: str
    organization: Optional[str] = None
    project: Optional[str] = None

    @property
    def fingerprint(self) -> str:
        return api_key_fingerprint(self.api_key)

    def headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        if self.project:
            headers["OpenAI-Project"] = self.project
        return headers

    def sdk_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if self.organization:
            kwargs["organization"] = self.organization
        if self.project:
            # Use an explicit header rather than the newer project= constructor
            # parameter so this remains compatible with older OpenAI v1 clients.
            kwargs["default_headers"] = {"OpenAI-Project": self.project}
        return kwargs


def _read_prefer_env(config_path: Path) -> bool:
    parser = configparser.ConfigParser()
    try:
        loaded = parser.read(config_path)
        if not loaded:
            logging.warning(
                "Config file '%s' is missing or unreadable; preferring "
                "OPENAI_API_KEY.",
                config_path,
            )
            return True
        return parser.getboolean("DEFAULT", "PreferEnvForAPIKey", fallback=True)
    except (configparser.Error, OSError, ValueError) as exc:
        logging.error("Failed to read OpenAI API key source preference: %s", exc)
        return True


def _read_file_api_key(token_file: Path) -> Optional[str]:
    try:
        raw_value = token_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise APIKeyConfigurationError(
            f"Could not read the OpenAI API key file '{token_file}': {exc}"
        ) from exc
    return _normalise_api_key(raw_value, str(token_file))


def load_openai_credentials(
    config_path: Path | str = CONFIG_PATH,
    token_file: Path | str = API_TOKEN_PATH,
) -> OpenAICredentials:
    """
    Resolve the OpenAI key once at startup.

    Project-scoped keys still use OPENAI_API_KEY and Bearer authentication.
    OPENAI_ORG_ID and OPENAI_PROJECT_ID are optional explicit routing overrides,
    not requirements for a project key.
    """
    config_path = Path(config_path)
    token_file = Path(token_file)
    prefer_env = _read_prefer_env(config_path)

    def read_environment() -> Optional[str]:
        return _normalise_api_key(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY")

    environment_source = ("OPENAI_API_KEY", read_environment)
    file_source = (str(token_file), lambda: _read_file_api_key(token_file))
    sources = (
        (environment_source, file_source)
        if prefer_env
        else (file_source, environment_source)
    )

    for source_index, (source_name, reader) in enumerate(sources):
        api_key = reader()
        if not api_key:
            continue

        if source_index > 0:
            logging.warning(
                "Preferred OpenAI key source was unavailable; falling back to %s. "
                "During rotation, confirm this is not a stale legacy key.",
                source_name,
            )

        credentials = OpenAICredentials(
            api_key=api_key,
            source=source_name,
            organization=_clean_optional(os.getenv("OPENAI_ORG_ID")),
            project=_clean_optional(os.getenv("OPENAI_PROJECT_ID")),
        )
        logging.info(
            "OpenAI credential loaded from %s (SHA-256 fingerprint: %s; "
            "secret not logged).",
            credentials.source,
            credentials.fingerprint,
        )
        if credentials.organization:
            logging.info("Explicit OpenAI organization override is configured.")
        if credentials.project:
            logging.info("Explicit OpenAI project override is configured.")
        return credentials

    raise APIKeyConfigurationError(
        "No OpenAI API key was found. Set a newly created project key in "
        "OPENAI_API_KEY (recommended) or place it in "
        f"'{token_file}'. Do not commit either secret to Git."
    )


def coerce_openai_credentials(value: Any = None) -> OpenAICredentials:
    """Resolve credentials from a credential object, bot object, key string, or env."""
    if isinstance(value, OpenAICredentials):
        return value

    if isinstance(value, str):
        api_key = _normalise_api_key(value, "explicit argument")
        if not api_key:
            raise APIKeyConfigurationError("The explicit OpenAI API key was empty.")
        return OpenAICredentials(api_key=api_key, source="explicit argument")

    if value is not None:
        nested = getattr(value, "openai_credentials", None)
        if isinstance(nested, OpenAICredentials):
            return nested

        api_key = getattr(value, "openai_api_key", None)
        if api_key:
            cleaned = _normalise_api_key(api_key, "bot.openai_api_key")
            if cleaned:
                return OpenAICredentials(
                    api_key=cleaned,
                    source="bot.openai_api_key",
                    organization=_clean_optional(
                        getattr(value, "openai_organization", None)
                    ),
                    project=_clean_optional(getattr(value, "openai_project", None)),
                )

    return load_openai_credentials()


def build_openai_headers(value: Any = None) -> Dict[str, str]:
    """Build explicit OpenAI HTTP headers without relying on module globals."""
    return coerce_openai_credentials(value).headers()


def get_api_key(
    config_path: Path | str = CONFIG_PATH,
    token_file: Path | str = API_TOKEN_PATH,
) -> str:
    """Compatibility wrapper for callers that only need the key string."""
    return load_openai_credentials(config_path, token_file).api_key


if __name__ == "__main__":
    try:
        credentials = load_openai_credentials()
    except APIKeyConfigurationError as exc:
        print(f"OpenAI credential check failed: {exc}")
        raise SystemExit(1) from exc

    print(
        "OpenAI credential loaded successfully from "
        f"{credentials.source}; fingerprint: {credentials.fingerprint}."
    )
