import asyncio
import configparser
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import api_get_duckduckgo_search as ddg
import web_search as web

DUMP = (Path(__file__).parent / "fixtures/news/duckduckgo-lynx.txt").read_bytes()


def test_direct_lynx_dump_joins_every_enabled_search_provider(monkeypatch):
    cfg = configparser.ConfigParser()
    cfg.read_string("[DuckDuckGo]\nEnabled=True\n[Perplexity]\nEnabled=True\n[WebSearch]\nOpenAIEnabled=True")
    monkeypatch.setattr(web, "config", cfg)
    monkeypatch.setattr(ddg, "enable_agentic_browsing", False)
    monkeypatch.setattr(ddg.httpx, "AsyncClient", Mock(side_effect=AssertionError("DDG must use Lynx for fetching")))
    started = []
    commands = []
    query = "  Amiwind latest news & Finland  "
    async def run():
        ready = asyncio.Event()
        async def start(name):
            started.append(name)
            if len(started) == 3:
                ready.set()
            await asyncio.wait_for(ready.wait(), 1)
        async def communicate():
            return DUMP, b""
        async def spawn(*args, **kwargs):
            commands.append((args, kwargs))
            await start("duckduckgo")
            return SimpleNamespace(returncode=0, communicate=AsyncMock(side_effect=communicate))
        async def perplexity(q, **kwargs):
            assert q == query
            await start("perplexity")
            return {"choices": [{"message": {"content": "Perplexity result [1]"}}],
                    "citations": ["https://example.org/perplexity"]}
        async def openai(q, bot):
            assert q == query
            await start("openai")
            return web.Evidence("OpenAI", "OpenAI result [O1]", {"O1": ("OpenAI", "https://example.org/openai")})
        monkeypatch.setattr(ddg.asyncio, "create_subprocess_exec", spawn)
        monkeypatch.setattr(web, "fact_check_with_perplexity", perplexity)
        monkeypatch.setattr(web, "openai_search", openai)
        function = {"name": "search_web", "arguments": json.dumps({"query": query})}
        completion = {"choices": [{"message": {"tool_calls": [
            {"id": "call1", "type": "function", "function": function}]}}]}
        request = AsyncMock(return_value={"choices": [{"message": {"content": "Combined answer"}}]})
        result, sources = await web.answer_web_tool(dict(function, tool_call_id="call1"), completion,
            [{"role": "system", "content": "Elasticsearch local fact"}], SimpleNamespace(timeout=2), request)
        messages = request.await_args.args[1]
        tool_messages = [message for message in messages if message["role"] == "tool"]
        assert len(tool_messages) == 1
        rows = json.loads(tool_messages[0]["content"])
        assert [row["provider"] for row in rows] == ["DuckDuckGo", "Perplexity", "OpenAI"]
        assert "Its CHIM engine streams the world" in rows[0]["evidence"]
        assert "https://github.com/FlyingFathead/amiwind" in rows[0]["evidence"]
        assert "Perplexity result" in rows[1]["evidence"] and "OpenAI result" in rows[2]["evidence"]
        assert messages[0]["content"] == "Elasticsearch local fact"
        assert len(sources) == 4
    asyncio.run(run())
    args, kwargs = commands[0]
    assert args[:4] == ("lynx", "-dump", "-width=200", "-display_charset=UTF-8")
    assert parse_qs(urlsplit(args[4]).query)["q"] == [query]
    assert kwargs["stdin"] == asyncio.subprocess.DEVNULL
    assert len(started) == 3 and len(commands) == 1


@pytest.mark.parametrize("kind", ["timeout", "cancellation"])
def test_lynx_process_is_killed_and_reaped(monkeypatch, kind):
    process = SimpleNamespace(returncode=None, kill=Mock(), wait=AsyncMock())
    async def run():
        ready = asyncio.Event()
        async def communicate():
            ready.set()
            await asyncio.Event().wait()
        process.communicate = communicate
        monkeypatch.setattr(ddg.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
        if kind == "timeout":
            with pytest.raises(asyncio.TimeoutError):
                await ddg._run_lynx_dump("https://example.org/", request_timeout=.02)
        else:
            task = asyncio.create_task(ddg._run_lynx_dump("https://example.org/"))
            await ready.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    asyncio.run(run())
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


@pytest.mark.parametrize("code,output", [(1, b"TLS failed"), (0, b"")])
def test_lynx_failures_are_explicit(monkeypatch, code, output):
    process = SimpleNamespace(returncode=code, communicate=AsyncMock(return_value=(output, b"fetch failed")))
    monkeypatch.setattr(ddg.asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(RuntimeError):
        asyncio.run(ddg._run_lynx_dump("https://example.org/"))
