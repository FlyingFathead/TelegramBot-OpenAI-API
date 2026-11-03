"""Retrieve dated, section-specific news for Elasticsearch actions."""
import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from dateutil.parser import isoparse, parse
import feedparser
import httpx

from app_version import VERSION
from config_paths import config
from news_sources import SOURCES
from web_search import CITATION, Evidence, RetrievalError, public_url, search_web, use_openai_fallback

logger = logging.getLogger(__name__)
UTC = timezone.utc
HELSINKI = ZoneInfo("Europe/Helsinki")
MAX_BYTES = 6 * 1024 * 1024


def _text(node):
    return node.get_text(" ", strip=True) if node else ""


def _rss(body):
    feed = feedparser.parse(body)
    for entry in feed.entries:
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        date = datetime(*stamp[:6], tzinfo=UTC) if stamp else None
        description = entry.get("summary", "")
        yield (entry.get("title"), entry.get("link"), date,
               _text(BeautifulSoup(description, "html.parser")) if description else "")


def _date(value, now):
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{1,2}:\d{2}", value):  # Iltalehti, today's local time
            return datetime.combine(now.astimezone(HELSINKI).date(),
                                    datetime.strptime(value, "%H:%M").time(), HELSINKI)
        relative = re.fullmatch(r"(\d+) (min\w*|hr\w*|hour\w*|day\w*) ago", value)
        if relative:
            unit = relative[2]
            seconds = 60 if unit.startswith("min") else 86400 if unit.startswith("day") else 3600
            return now - timedelta(seconds=int(relative[1]) * seconds)
        try:
            stamp = isoparse(value)
        except ValueError:
            stamp = parse(value, dayfirst=True) if re.search(r"\d{4}", value) else None
        if stamp and not stamp.tzinfo:
            stamp = stamp.replace(tzinfo=UTC)
        return stamp
    except (ValueError, OverflowError):
        return None


def _sanoma(soup, now):
    # Only the section's editorial lanes. Tickers and sidebars feature unrelated stories.
    state = soup.select_one("script#__NEXT_DATA__")
    if not state or not state.string:
        return
    page = json.loads(state.string)["props"]["pageProps"]["page"]
    for group in page["data"]["data"]:
        for lane in group.get("lanes", []):
            if lane.get("position") != "main":
                continue
            for item in lane.get("items", []):
                url = item.get("url") or ""
                if (item.get("itemType") != "standard" or "/mainos/" in url
                        or not re.search(r"/art-\d+\.html(?:[?#]|$)", url)):
                    continue
                yield item.get("title"), url, _date(item.get("displayDate"), now), item.get("ingress")


def _page(body, name, now):
    source = SOURCES[name]
    soup = BeautifulSoup(body, "lxml", from_encoding="utf-8")
    if source.domains[0] in ("is.fi", "hs.fi"):
        yield from _sanoma(soup, now)
        return
    if name.startswith("get_yle_"):
        if name == "get_yle_most_read":
            for link in soup.select('aside[aria-labelledby="sb-most-read"] h3 a[href]'):
                yield _text(link), link["href"], None, "Current most-read ranking. Article date unavailable."
            return
        main = soup.find("main")
        if not main:
            return
        for aside in main.select("aside"):
            aside.decompose()
        for link in main.select("a[data-card-heading-content-id][href]"):
            card = link.find_parent(attrs={"data-testid": "generic-story-background"})
            stamp = card.select("time[datetime]") if card else []
            yield (_text(link), link["href"], _date(stamp[-1]["datetime"], now) if stamp else None, "")
        return
    if name == "get_cnn_us_news":
        for link in soup.select('a[data-link-type="article"][href]'):
            path = urlsplit(link["href"]).path
            match = re.match(r"/(\d{4}/\d\d/\d\d)/us/", path)
            if match:
                yield (_text(link.select_one(".container__headline-text")), link["href"],
                       _date(match[1].replace("/", "-"), now), "")
        return
    for link in soup.select("main a[href]"):
        if name == "get_il_urheilu":
            if "/a/" not in link["href"]:
                continue
            headline = link.select_one(".front-title")
            date = _text(link.find("time"))
        else:  # BBC editorial cards
            if not re.match(r"/news/(articles|videos)/", urlsplit(link["href"]).path):
                continue
            headline = link.select_one("h2, h3")
            date = _text(link.select_one('[class*="MetaDataDate"], time'))
        yield _text(headline), link["href"], _date(date, now), _text(link.find("p"))


def news_evidence(body, name, method, now, days):
    source = SOURCES[name]
    rows = _rss(body) if method == "rss" else _page(body, name, now)
    result = Evidence(f"{source.label} ({method})")
    lines = []
    seen = set()
    for title, href, stamp, desc in rows:
        if not title or not href:
            continue
        url = urljoin(source.page, href).split("#")[0]
        if not public_url(url, source.domains) or url in seen:
            continue
        if stamp is None and not (method == "page" and name == "get_yle_most_read"):
            continue
        if stamp and not now - timedelta(days=days) <= stamp <= now + timedelta(minutes=10):
            continue
        seen.add(url)
        title = " ".join(unescape(title).split())[:250]
        detail = " ".join(unescape(desc or "").split())[:220]
        label = stamp.isoformat(timespec="minutes") if stamp else "Date unavailable"
        ref = result.cite("N", title, url)
        lines.append(f"{ref} {label}  {title}  {detail}".rstrip())
        if len(lines) >= 20:
            break
    if not lines:
        raise RetrievalError(f"No qualifying {method} articles")
    result.text = "\n".join(lines)
    return result


async def direct_news(client, name, method, now, days):
    source = SOURCES[name]
    url = source.rss if method == "rss" else source.page
    body = bytearray()
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";")[0].lower()
        if method == "page":
            if content_type not in ("text/html", "application/xhtml+xml"):
                raise RetrievalError("Expected an HTML section page")
            if str(response.url).split("?")[0].rstrip("/") != url.rstrip("/"):
                raise RetrievalError("Section redirected away from configured page")
        elif "xml" not in content_type and content_type != "application/rss":
            raise RetrievalError("Expected an XML news feed")
        async for chunk in response.aiter_bytes():
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise RetrievalError("Publisher response too large")
    return await asyncio.to_thread(news_evidence, bytes(body), name, method, now, days)


def dated_search_result(results, source, earliest, today):
    """A cited section page or a dated but stale story cannot establish today's news."""
    news = Evidence(source.label + " (web search)")
    lines = []
    for result in results:
        # Reserve space for every provider with usable dated evidence.
        limit = len(lines) + max(1, 20 // len(results))
        for line in result.text.splitlines():
            stamp = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", line)
            if not stamp:
                continue
            try:
                day = datetime.fromisoformat(stamp[1]).date()
            except ValueError:
                continue
            if not earliest <= day <= today:
                continue
            keys = set(CITATION.findall(line))
            for key, (title, url) in result.sources.items():
                if not public_url(url, source.domains) or (key not in keys and url not in line):
                    continue
                path = urlsplit(url).path.rstrip("/")
                if not path or path == urlsplit(source.page).path.rstrip("/"):
                    continue
                ref = news.cite("N", title, url)
                lines.append(f"{result.provider}: {day} {title} {ref}")
                if len(lines) >= limit:
                    break
            if len(lines) >= limit:
                break
    if not lines:
        raise RetrievalError("Search found no dated, cited articles for this section")
    news.text = "\n".join(lines)
    return news


async def fetch_news(name, bot=None):
    source = SOURCES[name]
    now = datetime.now(UTC)
    try:
        days = min(source.max_days, max(1, config.getint("WebSearch", "NewsMaxAgeDays", fallback=7)))
    except ValueError:
        days = min(source.max_days, 7)
    async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                 headers={"User-Agent": f"ChatKeke/{VERSION} (+https://chatkeke.fi)"}) as client:
        for method in ("rss", "openai", "page"):
            try:
                if method == "openai":
                    if not use_openai_fallback():
                        continue
                    earliest = (now - timedelta(days=days)).date()
                    query = (f"Find current {source.label} articles for the exact section {source.page}. "
                             f"Today is {now.date()}. Return only relevant articles published since {earliest}, "
                             "as one line per article: YYYY-MM-DD, headline, inline citation to that article. "
                             "For a regional or language edition, stay in that edition. "
                             "For rankings, only report a ranking confirmed by the publisher.")
                    found = await search_web(query, bot, domains=source.domains, recovery=True)
                    return dated_search_result(found, source, earliest, now.date())
                return await direct_news(client, name, method, now, days)
            except (httpx.HTTPError, RetrievalError, ValueError, KeyError, TypeError) as exc:
                logger.warning("%s %s failed: %s", name, method, exc)
    raise RetrievalError(f"No current articles could be retrieved for {source.label}")
