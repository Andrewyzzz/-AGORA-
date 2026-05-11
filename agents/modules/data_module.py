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
        """Fetch real-time market data and inject as structured context."""
        lines = ["[REAL-TIME MARKET DATA — use these numbers for any price-related predictions]"]

        # ── Crypto: BTC, ETH, SOL (CoinGecko, free) ──────────────────────────
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum,solana",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
                timeout=8,
            )
            data = resp.json()
            for coin_id, label in [("bitcoin","BTC"), ("ethereum","ETH"), ("solana","SOL")]:
                if coin_id in data:
                    p = data[coin_id]
                    lines.append(f"{label}/USD: ${p['usd']:,.2f} (24h: {p.get('usd_24h_change',0):+.1f}%)")
            # Gold via Yahoo Finance (more reliable)

        except Exception:
            pass

        # ── Equities: S&P500, Nasdaq, Dow (Yahoo Finance unofficial) ─────────
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            for ticker, label in [("^GSPC","S&P500"), ("^IXIC","Nasdaq"), ("^DJI","Dow Jones")]:
                try:
                    r = requests.get(
                        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                        headers=headers, timeout=6,
                        params={"interval":"1d","range":"2d"},
                    )
                    result = r.json()["chart"]["result"][0]
                    price  = result["meta"]["regularMarketPrice"]
                    prev   = result["meta"]["chartPreviousClose"]
                    chg    = (price - prev) / prev * 100
                    lines.append(f"{label}: {price:,.2f} ({chg:+.1f}%)")
                except Exception:
                    continue
        except Exception:
            pass

        # ── Commodities: Gold, WTI Oil, Brent Oil (Yahoo Finance) ───────────
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            for ticker, label in [("GC=F","Gold (XAU/USD)"), ("CL=F","WTI Oil"), ("BZ=F","Brent Oil")]:
                try:
                    r = requests.get(
                        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                        headers=headers, timeout=6,
                        params={"interval":"1d","range":"2d"},
                    )
                    result = r.json()["chart"]["result"][0]
                    price  = result["meta"]["regularMarketPrice"]
                    prev   = result["meta"]["chartPreviousClose"]
                    chg    = (price - prev) / prev * 100
                    unit = "/bbl" if "Oil" in label else "/oz"
                    lines.append(f"{label}: ${price:,.2f}{unit} ({chg:+.1f}%)")
                except Exception:
                    continue
        except Exception:
            pass

        # ── Forex: USD/EUR, USD/JPY (Frankfurter, free) ──────────────────────
        try:
            fx = requests.get(
                "https://api.frankfurter.app/latest?from=USD&to=EUR,JPY,CNY",
                timeout=5,
            ).json()
            if "rates" in fx:
                r = fx["rates"]
                lines.append(
                    f"USD/EUR: {r.get('EUR','?')} | "
                    f"USD/JPY: {r.get('JPY','?')} | "
                    f"USD/CNY: {r.get('CNY','?')}"
                )
        except Exception:
            pass

        # ── Fear & Greed Index (Alternative.me, free) ────────────────────────
        try:
            fng = requests.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=5,
            ).json()
            val = fng["data"][0]
            lines.append(
                f"Crypto Fear & Greed Index: {val['value']}/100 — {val['value_classification']}"
            )
        except Exception:
            pass

        return lines if len(lines) > 1 else []

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
