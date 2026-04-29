"""
Polymarket observation bridge — read-only price comparison for research.
Fetches public Polymarket data to benchmark against AGORA prices.
No trades are placed. Only public on-chain/API data is read.
"""
import requests
from dataclasses import dataclass

POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_API = "https://clob.polymarket.com"


@dataclass
class PolymarketMarket:
    condition_id: str
    question: str
    yes_price: float | None
    volume: float
    end_date: str


class PolymarketBridge:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "AGORA-Research/1.0"

    def search_market(self, question_keywords: str) -> PolymarketMarket | None:
        """Find a Polymarket market matching keywords."""
        try:
            resp = self.session.get(
                f"{POLYMARKET_GAMMA_API}/markets",
                params={"search": question_keywords, "limit": 5, "active": "true"},
                timeout=10,
            )
            resp.raise_for_status()
            markets = resp.json()
            if not markets:
                return None
            m = markets[0]
            return PolymarketMarket(
                condition_id=m.get("conditionId", ""),
                question=m.get("question", ""),
                yes_price=self._get_yes_price(m),
                volume=float(m.get("volume", 0)),
                end_date=m.get("endDate", ""),
            )
        except Exception:
            return None

    def _get_yes_price(self, market: dict) -> float | None:
        tokens = market.get("tokens", [])
        for t in tokens:
            if t.get("outcome", "").upper() == "YES":
                price = t.get("price")
                if price is not None:
                    return float(price)
        return None

    def get_price_by_condition_id(self, condition_id: str) -> float | None:
        """Get YES price for a known condition ID."""
        try:
            resp = self.session.get(
                f"{POLYMARKET_CLOB_API}/markets/{condition_id}",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            tokens = data.get("tokens", [])
            for t in tokens:
                if t.get("outcome", "").upper() == "YES":
                    return float(t.get("price", 0))
        except Exception:
            pass
        return None
