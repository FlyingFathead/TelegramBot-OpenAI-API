import asyncio
import ast
import configparser
import copy
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import web_search as web
import api_get_website_dump as website
import api_get_duckduckgo_search as ddg
from custom_functions import custom_functions
from openai_reasoning_compat import apply_reasoning_effort


def completion(name=None, arguments=None, call_id="call1", legacy=False, content=None):
    message = {"role": "assistant", "content": content}
    if name:
        function = {"name": name, "arguments": json.dumps(arguments)}
        if legacy:
            message["function_call"] = function
        else:
            message["tool_calls"] = [{"type": "function", "id": call_id, "function": function}]
    return {"choices": [{"message": message}]}


def call_from(response):
    message = response["choices"][0]["message"]
    if message.get("tool_calls"):
        tool, = message["tool_calls"]
        return dict(tool["function"], tool_call_id=tool["id"])
    return message["function_call"]


def chat_request():
    """Use the actual Chat Completions adapter and payload builder."""
    path = Path(__file__).resolve().parents[1] / "src/text_message_handler.py"
    names = {"make_api_request", "build_chat_payload", "build_openai_tools", "model_supports_temperature"}
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name in names]
    namespace = dict(httpx=httpx, json=json, apply_reasoning_effort=apply_reasoning_effort,
                     custom_functions=custom_functions, build_openai_headers=lambda bot: {"Authorization": "Bearer fake"})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["make_api_request"]


@pytest.mark.parametrize("legacy", [False, True])
def test_search_then_actual_website_tool_lynx_dump_then_answer(monkeypatch, legacy):
    first = completion("search_web", {"query": "AmiWind latest"}, legacy=legacy)
    followup = completion("get_website_dump", {"url": "https://example.org/article"}, "call2", legacy)
    final = completion(content="From local context, the search and the article [O1] [W2].")
    local = [{"role": "system", "content": "Elasticsearch RAG data: LOCAL_SENTINEL"},
             {"role": "user", "content": "Read the AmiWind article."}]
    before = copy.deepcopy(local)
    search = AsyncMock(return_value=[web.Evidence("OpenAI", "A result [O1]", {"O1": ("Story", "https://example.org/search")})])
    monkeypatch.setattr(web, "search_web", search)
    monkeypatch.setattr(website, "is_domain_allowed", lambda url: True)
    process = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"Full article from Lynx", b"")))
    lynx = AsyncMock(return_value=process)
    monkeypatch.setattr(ddg.asyncio, "create_subprocess_exec", lynx)
    chats = []
    def handle(request):
        assert request.method == "POST"  # Page fetches belong to Lynx.
        payload = json.loads(request.content)
        chats.append(payload)
        assert "LOCAL_SENTINEL" in json.dumps(payload["messages"])
        assert [tool["function"]["name"] for tool in payload["tools"]] == ["search_web", "get_website_dump"]
        assert payload["parallel_tool_calls"] is False
        assert payload["reasoning_effort"] == "none"
        return httpx.Response(200, json=followup if len(chats) == 1 else final)
    factory = httpx.AsyncClient
    monkeypatch.setattr(web.httpx, "AsyncClient", lambda **kw: factory(transport=httpx.MockTransport(handle), **kw))
    bot = SimpleNamespace(model="gpt-6-luna", reasoning_effort="none", timeout=5, logger=logging.getLogger("browsing-test"))
    result, sources = asyncio.run(web.answer_web_tool(call_from(first), first, local, bot, chat_request()))
    assert result == final and local == before
    search.assert_awaited_once_with("AmiWind latest", bot)
    lynx.assert_awaited_once()
    assert lynx.await_args.args == ("lynx", "-dump", "-width=200", "-display_charset=UTF-8", "https://example.org/article")
    process.communicate.assert_awaited_once_with()
    transcript = chats[-1]["messages"]
    assert "Full article from Lynx" in json.dumps(transcript)
    assert len([m for m in transcript if m["role"] in ("tool", "function")]) == 2
    assert sources == {"O1": ("Story", "https://example.org/search"), "W2": ("example.org", "https://example.org/article")}


def test_direct_browsing_then_another_page_retains_distinct_links(monkeypatch):
    config = configparser.ConfigParser()
    config.read_string("[DuckDuckGo]\nEnabled=False\n[Perplexity]\nEnabled=False\n[WebSearch]\nOpenAIEnabled=False\nUseOpenAIWebSearch=False\nFallbackToOpenAI=False")
    monkeypatch.setattr(web, "config", config)
    search = AsyncMock(side_effect=AssertionError("Direct browsing must not search"))
    monkeypatch.setattr(web, "search_web", search)
    assert {f["name"] for f in custom_functions} >= {"search_web", "get_website_dump"}
    first = completion("get_website_dump", {"url": "https://example.org/a"})
    followup = completion("get_website_dump", {"url": "https://example.org/b"}, "call2")
    final = completion(content="Both pages [W1] [W2]")
    dump = AsyncMock(side_effect=["First article", "Second article"])
    monkeypatch.setattr(website, "get_website_dump", dump)
    monkeypatch.setattr(website, "is_domain_allowed", lambda url: True)
    request = AsyncMock(side_effect=[followup, final])
    result, sources = asyncio.run(web.answer_web_tool(call_from(first), first, [], SimpleNamespace(timeout=5), request))
    assert result == final
    assert [c.args[0] for c in dump.await_args_list] == ["https://example.org/a", "https://example.org/b"]
    assert [source[1] for source in sources.values()] == ["https://example.org/a", "https://example.org/b"]
    transcript = request.await_args.args[1]
    assert '"W1"' in transcript[2]["content"] and '"W2"' in transcript[4]["content"]


def test_failed_page_read_returns_error_and_keeps_search_and_local_context(monkeypatch):
    first = completion("search_web", {"query": "q"})
    next_call = completion("get_website_dump", {"url": "https://example.org/blocked"}, "call2")
    final = completion(content="The page failed; these are the search findings.")
    monkeypatch.setattr(web, "search_web", AsyncMock(return_value=[web.Evidence("DuckDuckGo", "Search finding")]))
    monkeypatch.setattr(web, "website_evidence", AsyncMock(side_effect=web.RetrievalError("Page unavailable")))
    request = AsyncMock(side_effect=[next_call, final])
    local = [{"role": "system", "content": "local fact"}]
    asyncio.run(web.answer_web_tool(call_from(first), first, local, SimpleNamespace(timeout=5), request))
    transcript = request.await_args.args[1]
    assert transcript[0] == local[0]
    assert "Search finding" in json.dumps(transcript)
    assert json.loads(transcript[-1]["content"])["status"] == "unavailable"


def test_browsing_budget_stops_further_calls(monkeypatch):
    cfg = configparser.ConfigParser()
    cfg.read_string("[WebSearch]\nMaxWebToolCalls=2")
    monkeypatch.setattr(web, "config", cfg)
    first = completion("get_website_dump", {"url": "https://example.org/a"})
    more = completion("get_website_dump", {"url": "https://example.org/b"}, "call2")
    dump = AsyncMock(return_value=[web.Evidence("Website", "Article")])
    monkeypatch.setattr(web, "website_evidence", dump)
    request = AsyncMock(side_effect=[more, completion(content="Final")])
    asyncio.run(web.answer_web_tool(call_from(first), first, [], SimpleNamespace(timeout=5), request))
    assert dump.await_count == 2
    assert request.await_args_list[0].kwargs["include_functions"] is True
    assert request.await_args_list[1].kwargs == {"include_functions": False}


def test_unrelated_function_is_not_executed(monkeypatch):
    first = completion("get_website_dump", {"url": "https://example.org/a"})
    unrelated = completion("manage_reminder", {"action": "delete", "id": 1}, "call2")
    dump = AsyncMock(return_value=[web.Evidence("Website", "Article")])
    monkeypatch.setattr(web, "website_evidence", dump)
    request = AsyncMock(side_effect=[unrelated, completion(content="Done")])
    asyncio.run(web.answer_web_tool(call_from(first), first, [], SimpleNamespace(timeout=5), request))
    dump.assert_awaited_once()
    assert json.loads(request.await_args.args[1][-1]["content"])["status"] == "unavailable"
