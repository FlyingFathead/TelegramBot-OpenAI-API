import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import news_webpage_parser as news
import elasticsearch_functions as es
from web_search import Evidence, RetrievalError

FIXTURES = Path(__file__).parent / "fixtures" / "news"
NOW = datetime(2026, 11, 3, 16, tzinfo=timezone.utc)


def test_sanoma_uses_section_and_filters_age_duplicates_ads_and_sidebars():
    r = news.news_evidence((FIXTURES / "sanoma.html").read_bytes(), "get_is_jaakiekko", "page", NOW, 7)
    assert r.sources == {"N1": ("Joukkue & valmentaja", "https://www.is.fi/jaakiekko/art-101.html")}
    assert "Ottelun ennakko" in r.text


def test_yle_region_and_rankings_have_distinct_selectors():
    data = (FIXTURES / "yle.html").read_bytes()
    local = news.news_evidence(data, "get_yle_kainuu", "page", NOW, 7)
    ranked = news.news_evidence(data, "get_yle_most_read", "page", NOW, 7)
    assert local.sources["N1"][1].endswith("/74-1")
    assert ranked.sources["N1"][1].endswith("/74-2") and "unavailable" in ranked.text


@pytest.mark.parametrize("status,mime,body", [
    (404, "text/html", b"Not found"), (200, "text/html", b"<html>Consent</html>"),
    (200, "application/rss+xml", b"<rss><channel/></rss>"),
    (200, "application/rss+xml", b"<rss><channel><item><title>Old</title><link>https://yle.fi/a/1</link>"
                                 b"<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item></channel></rss>")])
def test_bad_rss_calls_scoped_openai_next(monkeypatch, status, mime, body):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"Content-Type": mime}, content=body)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(news.httpx, "AsyncClient", lambda **kw: client)
    monkeypatch.setattr(news, "use_openai_fallback", lambda: True)
    today = datetime.now(timezone.utc).date()
    found = Evidence("OpenAI", f"{today} Kainuun uutinen [O1]",
                     {"O1": ("Kainuun uutinen", "https://yle.fi/a/74-1")})
    search = AsyncMock(return_value=[found])
    monkeypatch.setattr(news, "search_web", search)
    sources = {}
    messages = asyncio.run(es.action_token_functions["<[get_yle_kainuu]>"](None, None, [], bot="bot",
                                                                          sources=sources))
    assert calls == [news.SOURCES["get_yle_kainuu"].rss]
    assert search.await_count == 1 and search.await_args.kwargs["domains"] == ("yle.fi",)
    assert "Kainuun" in search.await_args.args[0] and search.await_args.args[1] == "bot"
    assert sources["N1"][1] in messages[-1]["content"]


def test_healthy_feed_skips_secondary_sources(monkeypatch):
    direct = AsyncMock(return_value=Evidence("rss", "news"))
    search = AsyncMock()
    monkeypatch.setattr(news, "direct_news", direct)
    monkeypatch.setattr(news, "search_web", search)
    assert asyncio.run(news.fetch_news("get_yle_news")).text == "news"
    assert direct.await_count == 1 and direct.await_args.args[2] == "rss"
    search.assert_not_awaited()


@pytest.mark.parametrize("enabled,expected", [(True, ["rss", "openai", "page"]), (False, ["rss", "page"])])
def test_page_after_disabled_or_failed_openai(monkeypatch, enabled, expected):
    calls = []
    async def direct(client, name, method, now, days):
        calls.append(method)
        if method == "rss":
            raise RetrievalError("empty feed")
        return Evidence("page", "page headline")
    async def unavailable(*args, **kwargs):
        calls.append("openai")
        raise RetrievalError("outage")
    monkeypatch.setattr(news, "direct_news", direct)
    monkeypatch.setattr(news, "use_openai_fallback", lambda: enabled)
    monkeypatch.setattr(news, "search_web", unavailable)
    assert asyncio.run(news.fetch_news("get_hs_tiede")).text == "page headline"
    assert calls == expected


def test_news_token_failure_is_not_reported_as_news(monkeypatch):
    monkeypatch.setattr(es, "fetch_news", AsyncMock(side_effect=RetrievalError("no current articles")))
    history = [{"role": "user", "content": "news"}]
    messages = asyncio.run(es.action_token_functions["<[get_hs_tiede]>"](None, None, history))
    assert len(history) == 1 and "retrieval failed" in messages[-1]["content"]
    assert len(es.news_actions) == 85


def test_scoped_search_rejects_stale_or_uncited_and_generic_section_links():
    section = news.SOURCES["get_hs_tiede"]
    r = Evidence("OpenAI", "2001-01-01 old [O1]\n2026-11-03 uncited\n2026-11-03 index [O2]",
                 {"O1": ("old", "https://www.hs.fi/tiede/art-1.html"), "O2": ("index", section.page)})
    with pytest.raises(RetrievalError):
        news.dated_search_result([r], section, NOW.date(), NOW.date())


def test_generic_legacy_rss_token_has_an_explicit_failure():
    messages = asyncio.run(es.action_token_functions["<[fetch_rss]>"](None, None, []))
    assert "No feed is configured" in messages[-1]["content"]
