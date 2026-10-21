#!/usr/bin/env python3
"""Verify ChatKeke's configured OpenAI project key without printing it."""

from __future__ import annotations

import argparse
import configparser
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from api_key import APIKeyConfigurationError, load_openai_credentials  # noqa: E402
from config_paths import CONFIG_PATH  # noqa: E402

API_BASE_URL = "https://api.openai.com/v1"


def _configured_model() -> str:
    parser = configparser.ConfigParser()
    try:
        parser.read(CONFIG_PATH)
        return parser.get("DEFAULT", "Model", fallback="gpt-4o-mini").strip()
    except (configparser.Error, OSError, ValueError):
        return "gpt-4o-mini"


def _response_detail(response: httpx.Response) -> str:
    request_id = response.headers.get("x-request-id") or response.headers.get(
        "openai-request-id"
    )
    detail = f"HTTP {response.status_code}"
    if request_id:
        detail += f", request ID {request_id}"
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error = payload["error"]
        if error.get("type"):
            detail += f", type {error['type']}"
        if error.get("message"):
            detail += f": {error['message']}"
    return detail


def verify_models_access(client: httpx.Client) -> None:
    response = client.get(f"{API_BASE_URL}/models")
    if response.is_success:
        print("Project access check: PASS (/v1/models accepted the key).")
        return
    if response.status_code == 401:
        raise RuntimeError(
            "The key is invalid, revoked, incomplete, or expired: "
            + _response_detail(response)
        )
    if response.status_code == 403:
        raise RuntimeError(
            "The key authenticated but lacks model-list permission: "
            + _response_detail(response)
        )
    raise RuntimeError("Project access check failed: " + _response_detail(response))


def verify_chat_completion(client: httpx.Client, model: str) -> None:
    token_key = "max_tokens" if model.strip().lower().startswith("gpt-4") else "max_completion_tokens"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        token_key: 16,
    }
    response = client.post(
        f"{API_BASE_URL}/chat/completions",
        json=payload,
    )
    if not response.is_success:
        raise RuntimeError(
            f"Live Chat Completions check failed for '{model}': "
            + _response_detail(response)
        )
    print(f"Live Chat Completions check: PASS (model: {model}).")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify ChatKeke's OpenAI project key without printing it."
    )
    parser.add_argument(
        "--live-request",
        action="store_true",
        help="send one tiny Chat Completions request instead of listing models",
    )
    parser.add_argument("--model", help="model for --live-request")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    try:
        credentials = load_openai_credentials()
    except APIKeyConfigurationError as exc:
        print(f"Credential loading failed: {exc}", file=sys.stderr)
        return 1

    print(f"Loaded source: {credentials.source}")
    print(f"SHA-256 fingerprint: {credentials.fingerprint}")
    print("The secret value was not printed.")

    try:
        with httpx.Client(headers=credentials.headers(), timeout=args.timeout) as client:
            if args.live_request:
                verify_chat_completion(client, args.model or _configured_model())
            else:
                verify_models_access(client)
    except (httpx.HTTPError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
