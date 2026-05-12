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

    def get_diverse_markets(self, limit: int = 20) -> list[dict]:
        """
        Fetch diverse high-volume Polymarket markets across multiple categories.
        Used to inspire agent proposals with variety beyond news headlines.
        """
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) + timedelta(days=3)
        categories = [
            ("politics", "election OR congress OR president OR senate"),
            ("finance", "federal reserve OR interest rate OR inflation OR GDP"),
            ("crypto", "bitcoin OR ethereum OR crypto"),
            ("sports", "championship OR world cup OR tournament OR league"),
            ("science", "FDA OR vaccine OR climate OR space"),
            ("geopolitics", "ceasefire OR treaty OR sanctions OR summit"),
        ]
        results = []
        for _, query in categories:
            try:
                resp = self.session.get(
                    f"{POLYMARKET_GAMMA_API}/markets",
                    params={"active": "true", "closed": "false",
                            "limit": 5, "order": "volume",
                            "ascending": "false", "volume_num_min": 5000},
                    timeout=8,
                )
                if resp.status_code != 200:
                    continue
                for m in resp.json():
                    q = m.get("question", "").lower()
                    if any(kw in q for kw in ["up or down", "above or below"]):
                        continue
                    end_str = m.get("endDate", "")[:10]
                    try:
                        end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        if end_dt < cutoff:
                            continue
                    except Exception:
                        continue
                    yes_price = self._get_yes_price(m)
                    entry = {
                        "question": m.get("question", ""),
                        "yes_price": yes_price,
                        "end_date": end_str,
                        "volume": round(float(m.get("volume", 0)), 0),
                    }
                    if entry not in results:
                        results.append(entry)
            except Exception:
                continue
        return results[:limit]

    def get_recent_markets(self, limit: int = 15, min_days_to_resolve: int = 3) -> list[dict]:
        """
        Fetch recently listed active Polymarket markets for agent inspiration.
        Filters out ultra-short-term (intraday) price-up/down markets.
        Returns markets resolving at least `min_days_to_resolve` days from now.
        Read-only — no trades placed.
        """
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) + timedelta(days=min_days_to_resolve)

        try:
            # Fetch more than needed to allow filtering
            resp = self.session.get(
                f"{POLYMARKET_GAMMA_API}/markets",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": 100,
                    "order": "volume",      # sort by volume — more liquid = more meaningful
                    "ascending": "false",
                    "volume_num_min": 1000, # at least $1k volume
                },
                timeout=10,
            )
            resp.raise_for_status()
            markets = resp.json()

            results = []
            skip_keywords = {"up or down", "above or below", "higher or lower", "price at"}
            for m in markets:
                q = m.get("question", "").lower()
                # Skip intraday price-movement markets
                if any(kw in q for kw in skip_keywords):
                    continue
                # Skip if resolves too soon
                end_str = m.get("endDate", "")[:10]
                try:
                    end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if end_dt < cutoff:
                        continue
                except Exception:
                    continue

                yes_price = self._get_yes_price(m)
                results.append({
                    "question":  m.get("question", ""),
                    "yes_price": yes_price,
                    "end_date":  end_str,
                    "volume":    round(float(m.get("volume", 0)), 0),
                })
                if len(results) >= limit:
                    break

            return results
        except Exception:
            return []

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
