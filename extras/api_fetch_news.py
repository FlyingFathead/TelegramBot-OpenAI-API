# api_fetch_news.py

import httpx

async def fetch_news(api_key: str, query: str):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": api_key,
        "language": "en",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            news_data = response.json()
            articles = news_data.get("articles", [])
            messages = []
            for article in articles[:5]:  # Limit to the first 5 articles
                title = article["title"]
                url = article["url"]
                messages.append(f"{title}\nRead more: {url}")
            return "\n\n".join(messages)
        else:
            return "Failed to fetch news."
