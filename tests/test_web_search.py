import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import web_search as web
from custom_functions import custom_functions


def response(url="https://yle.fi/a/74-100?x=1&y=2"):
    return {"status": "completed", "output": [
        {"type": "web_search_call", "status": "completed"},
        {"type": "message", "content": [{"type": "output_text", "text": "An article.",
          "annotations": [{"type": "url_citation", "start_index": 10, "end_index": 11,
                           "title": "A <headline>", "url": url}]}]}]}


def test_openai_request_uses_existing_credentials_and_exact_query(monkeypatch):
    query = "  jääkiekko & SM-liiga?  "
    monkeypatch.setattr(web, "providers", lambda: ["openai"])
    def handler(request):
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.headers["OpenAI-Project"] == "test-project"
        data = json.loads(request.content)
        assert data["input"] == query and data["model"] == "gpt-6-luna"
        assert data["tool_choice"] == "required" and data["max_tool_calls"] == 1
        assert data["tools"] == [{"type": "web_search", "external_web_access": True,
                                   "filters": {"allowed_domains": ["yle.fi"]}}]
        return httpx.Response(200, json=response())
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(web.httpx, "AsyncClient", lambda **kw: client)
    bot = SimpleNamespace(openai_api_key="test-key", openai_project="test-project")
    result = asyncio.run(web.openai_search(query, bot, domains=("yle.fi",)))
    assert result.sources["O1"][0] == "A <headline>"
    assert "[O1]" in result.text
    assert '<a href="https://yle.fi/a/74-100?x=1&amp;y=2">[O1]</a>' in web.telegram_evidence_parts(
        "Uutinen [O1]", result.sources)[0]


@pytest.mark.parametrize("change", ["failed", "missing_search", "no_citation", "wrong_domain"])
def test_uncited_incomplete_or_out_of_scope_is_a_failure(change):
    raw = response("https://yle.fi.attacker.example/" if change == "wrong_domain" else "https://yle.fi/a/1")
    if change == "failed":
        raw["status"] = "incomplete"
    if change == "missing_search":
        raw["output"].pop(0)
    if change == "no_citation":
        raw["output"][1]["content"][0]["annotations"] = []
    with pytest.raises(web.RetrievalError):
        web.parse_openai(raw, ("yle.fi",))


def test_three_providers_start_together_and_keep_finished_results_at_deadline(monkeypatch):
    query = "  exactly this query  "
    names = ["duckduckgo", "perplexity", "openai"]
    calls = []
    cancelled = []
    async def run():
        started = asyncio.Event()
        async def provider(name, value, bot):
            calls.append((name, value))
            if len(calls) == 3:
                started.set()
            await started.wait()
            if name == "perplexity":
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(name)
            return web.Evidence(name, "found")
        monkeypatch.setattr(web, "_provider", provider)
        monkeypatch.setattr(web, "providers", lambda: names)
        monkeypatch.setattr(web, "search_timeout", lambda: .08)
        return await asyncio.wait_for(web.search_web(query, None, "combined"), .7)
    assert [r.provider for r in asyncio.run(run())] == ["duckduckgo", "openai"]
    assert calls == [(name, query) for name in names]
    assert cancelled == ["perplexity"]


@pytest.mark.parametrize("name,argkey", [
    ("search_web", "query"), ("get_duckduckgo_search", "search_query"), ("query_perplexity", "question"),
])
def test_shared_tool_sends_only_query_and_returns_one_tool_result(monkeypatch, name, argkey):
    names = [f["name"] for f in custom_functions if f["name"] in web.WEB_TOOL_NAMES]
    assert names == ["search_web"]
    query = "Suomen jääkiekkouutiset"
    fn = {"name": name, "arguments": json.dumps({argkey: query})}
    raw = {"choices": [{"message": {"tool_calls": [{"type": "function", "id": "call1", "function": fn}]}}]}
    done = {"choices": [{"message": {"content": "Yhteenveto"}}]}
    from configparser import ConfigParser
    config = ConfigParser()
    if name != "search_web":
        config.read_string("[Perplexity]\nEnabled=True")
    monkeypatch.setattr(web, "config", config)
    expected = ["duckduckgo", "openai"] if name == "search_web" else ["duckduckgo", "perplexity", "openai"]
    search = AsyncMock(side_effect=lambda provider, q, bot: web.Evidence(provider, "Found " + provider))
    request = AsyncMock(return_value=done)
    monkeypatch.setattr(web, "_provider", search)
    bot = SimpleNamespace(timeout=31)
    messages = [{"role": "user", "content": "private chat sentinel"}]
    result, _ = asyncio.run(web.answer_web_tool(dict(fn, tool_call_id="call1"), raw, messages, bot, request))
    assert [call.args for call in search.await_args_list] == [(provider, query, bot) for provider in expected]
    assert result == done and request.await_count == 1 and len(messages) == 1
    transcript = request.await_args.args[1]
    assert transcript[-1]["role"] == "tool" and transcript[-1]["tool_call_id"] == "call1"
    assert sum(message["role"] == "tool" for message in transcript) == 1
    assert [row["evidence"] for row in json.loads(transcript[-1]["content"])] == ["Found " + p for p in expected]
    assert request.await_args.kwargs == {"include_functions": True, "function_names": ("search_web", "get_website_dump")}


def test_combined_skips_disabled_and_isolates_errors(monkeypatch):
    async def run(name, query, bot):
        assert name != "perplexity"
        if name == "openai":
            raise web.RetrievalError("HTTP 429")
        return web.Evidence(name, "found")
    monkeypatch.setattr(web, "providers", lambda: ["duckduckgo", "openai"])
    monkeypatch.setattr(web, "run_provider", run)
    assert [r.provider for r in asyncio.run(web.search_web("q", None, "combined"))] == ["duckduckgo"]
    with pytest.raises(web.RetrievalError, match="unavailable"):
        asyncio.run(web.search_web("q", None, "perplexity"))
    monkeypatch.setattr(web, "run_provider", AsyncMock(side_effect=web.RetrievalError("down")))
    with pytest.raises(web.RetrievalError, match="All"):
        asyncio.run(web.search_web("q", None, "combined"))


def test_single_failure_uses_openai_once_with_same_query(monkeypatch):
    run = AsyncMock(side_effect=[web.RetrievalError("down"), web.Evidence("OpenAI", "found")])
    monkeypatch.setattr(web, "run_provider", run)
    monkeypatch.setattr(web, "use_openai_fallback", lambda: True)
    assert "fallback" in asyncio.run(web.search_web("q", None, "duckduckgo"))[0].provider
    assert [c.args[:2] for c in run.await_args_list] == [("duckduckgo", "q"), ("openai", "q")]


def test_http_error_can_fail_without_a_second_openai_call(monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(429)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(web.httpx, "AsyncClient", lambda **kw: client)
    with pytest.raises(web.RetrievalError):
        asyncio.run(web.search_web("q", "test-key", "openai"))
    assert len(requests) == 1


def test_citations_survive_splitting_and_omitted_markers():
    sources = {"O1": ("Title <here>", "https://example.org/x?a=1&b=2")}
    blocks = web.telegram_evidence_parts("🐒" * 1898 + "[O1] " + "X" * 1000, sources)
    assert len(blocks) == 2 and all(b.count("<a ") == b.count("</a>") for b in blocks)
    assert any('>[O1]</a>' in b for b in blocks)
    block, = web.telegram_evidence_parts("A <result>", sources)
    assert "Title &lt;here&gt;" in block and "&amp;b=2" in block


def test_actual_provider_adapters_receive_only_tool_query_and_common_timeout(monkeypatch):
    query = "julkaisu tänään"
    ddg = AsyncMock(return_value="Report https://example.fi/one")
    pplx = AsyncMock(return_value={"choices": [{"message": {"content": "Two [1]"}}],
                                 "citations": ["https://example.fi/two"]})
    openai = AsyncMock(return_value=web.Evidence("OpenAI web search", "Three"))
    monkeypatch.setattr(web, "get_duckduckgo_search", ddg)
    monkeypatch.setattr(web, "fact_check_with_perplexity", pplx)
    monkeypatch.setattr(web, "openai_search", openai)
    monkeypatch.setattr(web, "providers", lambda: ["duckduckgo", "perplexity", "openai"])
    monkeypatch.setattr(web, "search_timeout", lambda: 17)
    monkeypatch.setitem(web.config["WebSearch"], "DefaultProvider", "combined")
    results = asyncio.run(web.search_web(query, "bot"))
    assert [r.provider for r in results] == ["DuckDuckGo", "Perplexity", "OpenAI web search"]
    ddg.assert_awaited_once_with(query, query, openai_auth="bot", request_timeout=17)
    pplx.assert_awaited_once_with(query, request_timeout=17)
    openai.assert_awaited_once_with(query, "bot")
    assert results[1].text == "Two [P1]"


def test_website_fallback_is_scoped_to_the_tool_url(monkeypatch):
    import api_get_website_dump as dump
    url = "https://example.org/section"
    search = AsyncMock(return_value=[web.Evidence("OpenAI", "cached evidence")])
    monkeypatch.setattr(dump, "get_website_dump", AsyncMock(return_value="Error: HTTP 404"))
    monkeypatch.setattr(web, "use_openai_fallback", lambda: True)
    monkeypatch.setattr(web, "search_web", search)
    assert "direct website retrieval failed" in asyncio.run(web.website_evidence(url, "bot"))[0].provider
    search.assert_awaited_once_with(url, "bot", domains=("example.org",), recovery=True)
    monkeypatch.setattr(dump, "is_domain_allowed", lambda _url: False)
    with pytest.raises(web.RetrievalError):
        asyncio.run(web.website_evidence(url, "bot"))
    assert search.await_count == 1


def test_duckduckgo_rejects_challenge_dump(monkeypatch):
    import api_get_duckduckgo_search as ddg
    monkeypatch.setattr(ddg, "_run_lynx_dump", AsyncMock(return_value=
        "Unfortunately, bots use DuckDuckGo too.\nReferences\n1. https://duck.co/feedback"))
    with pytest.raises(RuntimeError, match="no result links"):
        asyncio.run(ddg._fetch_duckduckgo_results("needle", request_timeout=11))


@pytest.mark.parametrize("ddg,pplx,openai", [
    (d, p, o) for d in (False, True) for p in (False, True) for o in (False, True)
])
def test_model_search_uses_every_enabled_source(monkeypatch, ddg, pplx, openai):
    monkeypatch.setitem(web.config["DuckDuckGo"], "Enabled", str(ddg))
    monkeypatch.setitem(web.config["Perplexity"], "Enabled", str(pplx))
    monkeypatch.setitem(web.config["WebSearch"], "UseOpenAIWebSearch", str(openai))
    monkeypatch.setitem(web.config["WebSearch"], "DefaultProvider", "duckduckgo")
    async def provider(name, query, bot):
        assert query == "only this query"
        return web.Evidence(name, "evidence from " + name)
    run = AsyncMock(side_effect=provider)
    monkeypatch.setattr(web, "run_provider", run)
    expected = [n for n, active in [("duckduckgo", ddg), ("perplexity", pplx), ("openai", openai)] if active]
    if not expected:
        with pytest.raises(web.RetrievalError, match="No search providers"):
            asyncio.run(web.search_web("only this query", None))
    else:
        results = asyncio.run(web.search_web("only this query", None))
        assert [r.text for r in results] == ["evidence from " + n for n in expected]
    assert [call.args[0] for call in run.await_args_list] == expected


@pytest.mark.parametrize("fallback", [True, False])
def test_initial_flag_independent_of_fallback(monkeypatch, fallback):
    monkeypatch.setitem(web.config["DuckDuckGo"], "Enabled", "True")
    monkeypatch.setitem(web.config["Perplexity"], "Enabled", "False")
    monkeypatch.setitem(web.config["WebSearch"], "UseOpenAIWebSearch", "False")
    monkeypatch.setitem(web.config["WebSearch"], "FallbackToOpenAI", str(fallback))
    run = AsyncMock(side_effect=[web.RetrievalError("failure"), web.Evidence("OpenAI", "found")])
    monkeypatch.setattr(web, "run_provider", run)
    if fallback:
        assert asyncio.run(web.search_web("q", None))[0].text == "found"
    else:
        with pytest.raises(web.RetrievalError):
            asyncio.run(web.search_web("q", None))
    assert [c.args[0] for c in run.await_args_list] == (["duckduckgo", "openai"] if fallback else ["duckduckgo"])
