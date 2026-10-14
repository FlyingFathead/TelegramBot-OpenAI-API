import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import api_perplexity_search  # noqa: E402


def test_default_endpoint_sends_integration_header(monkeypatch):
    monkeypatch.setattr(
        api_perplexity_search,
        "PERPLEXITY_ENDPOINT",
        "https://api.perplexity.ai/chat/completions",
    )
    headers = api_perplexity_search._perplexity_headers()
    assert headers["X-Pplx-Integration"] == "telegrambot-openai-api"
    assert [k.lower() for k in headers].count("x-pplx-integration") == 1


def test_custom_endpoint_omits_integration_header(monkeypatch):
    for endpoint in (
        "https://proxy.example.com/chat/completions",
        "https://api.perplexity.ai.example.com/chat/completions",
    ):
        monkeypatch.setattr(api_perplexity_search, "PERPLEXITY_ENDPOINT", endpoint)
        headers = api_perplexity_search._perplexity_headers()
        assert "X-Pplx-Integration" not in headers
