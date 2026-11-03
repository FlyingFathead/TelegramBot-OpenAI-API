"""Exercise the bot's retrieval backends without starting Telegram or Elasticsearch."""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from news_sources import SOURCES
from news_webpage_parser import fetch_news
from web_search import RetrievalError, search_web


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Run a search with the bot's credentials and config")
    search.add_argument("query")
    search.add_argument("--provider", choices=("auto", "duckduckgo", "perplexity", "openai", "combined"),
                        default="auto")
    news = commands.add_parser("news", help="Run one Elasticsearch news action")
    news.add_argument("action", choices=sorted(SOURCES))
    args = parser.parse_args()
    try:
        if args.command == "news":
            results = [await fetch_news(args.action)]
        else:
            results = await search_web(args.query, None, provider=args.provider)
    except RetrievalError as exc:
        parser.exit(1, f"{exc}\n")
    for result in results:
        print(result.context())


if __name__ == "__main__":
    asyncio.run(main())
