"""
Data ingestion module — fetches recent news for agent decision-making.
Sources: NewsAPI + Reuters/AP RSS feeds (no API key required for RSS).
"""
import os
import time
import feedparser
import requests
from dataclasses import dataclass

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/topNews",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.skynews.com/feeds/rss/world.xml",
]

CRYPTO_RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
]


@dataclass
class NewsItem:
    title: str
    summary: str
    published: str
    source: str

    def to_str(self) -> str:
        return f"[{self.source}] {self.title}: {self.summary[:200]}"


class DataModule:
    def __init__(self, newsapi_key: str | None = None, cache_ttl: int = 300):
        self.newsapi_key = newsapi_key or os.environ.get("NEWSAPI_KEY")
        self.cache_ttl = cache_ttl
        self._cache: list[NewsItem] = []
        self._cache_time: float = 0

    def get_recent_news(self, max_items: int = 20) -> list[str]:
        if time.time() - self._cache_time < self.cache_ttl and self._cache:
            prices = self._fetch_prices()
            return prices + [item.to_str() for item in self._cache[:max_items]]

        items = []
        items.extend(self._fetch_rss(RSS_FEEDS + CRYPTO_RSS_FEEDS))
        if self.newsapi_key:
            items.extend(self._fetch_newsapi())

        self._cache = items[:50]
        self._cache_time = time.time()
        prices = self._fetch_prices()
        return prices + [item.to_str() for item in items[:max_items]]

    def _fetch_prices(self) -> list[str]:
        """Fetch real-time prices from CoinGecko and inject as context."""
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum,gold",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            lines = ["[REAL-TIME MARKET PRICES — use these for any price-related predictions]"]
            if "bitcoin" in data:
                p = data["bitcoin"]
                lines.append(f"BTC/USD: ${p['usd']:,.0f} (24h change: {p.get('usd_24h_change', 0):.1f}%)")
            if "ethereum" in data:
                p = data["ethereum"]
                lines.append(f"ETH/USD: ${p['usd']:,.0f} (24h change: {p.get('usd_24h_change', 0):.1f}%)")
            if "gold" in data:
                p = data["gold"]
                lines.append(f"Gold (XAU/USD): ${p['usd']:,.0f}")
            # Also try to get DXY from a simple source
            try:
                fx = requests.get(
                    "https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY",
                    timeout=5,
                ).json()
                if "rates" in fx:
                    lines.append(f"USD/EUR: {fx['rates'].get('EUR', '?')} | USD/GBP: {fx['rates'].get('GBP', '?')}")
            except Exception:
                pass
            return lines
        except Exception:
            return []

    def _fetch_rss(self, feeds: list[str]) -> list[NewsItem]:
        items = []
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                source = feed.feed.get("title", url.split("/")[2])
                for entry in feed.entries[:5]:
                    items.append(NewsItem(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", entry.get("description", "")),
                        published=entry.get("published", ""),
                        source=source,
                    ))
            except Exception:
                continue
        return items

    def _fetch_newsapi(self) -> list[NewsItem]:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"language": "en", "pageSize": 20, "apiKey": self.newsapi_key},
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            return [
                NewsItem(
                    title=a["title"] or "",
                    summary=a.get("description") or "",
                    published=a.get("publishedAt", ""),
                    source=a.get("source", {}).get("name", "NewsAPI"),
                )
                for a in articles if a.get("title")
            ]
        except Exception:
            return []
