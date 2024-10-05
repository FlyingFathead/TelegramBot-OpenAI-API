# rss_feeds.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import feedparser
from utils import sanitize_html, split_message

RSS_FEED_URLS = {
    'is_tuoreimmat': 'https://www.is.fi/rss/tuoreimmat.xml',
    'your_custom_rss': 'http://example.com/rss'
    # Add more RSS feed URLs as needed
}

async def fetch_rss_feed(feed_key):
    """Fetch and format the RSS feed based on the feed key."""
    feed_url = RSS_FEED_URLS.get(feed_key)
    if not feed_url:
        return f"Unknown RSS feed key: {feed_key}"
    
    feed = feedparser.parse(feed_url)
    formatted_entries = "\n".join([f"{entry.title}: {entry.link}" for entry in feed.entries[:5]])
    return formatted_entries
