"""
AGORA Dashboard Backend — with in-memory cache for fast responses.
All on-chain data is refreshed every 30s in the background.
API requests return from cache immediately (<5ms).
"""
import os
import json
import sqlite3
import time
import asyncio
import threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

ROOT = Path(os.environ.get("AGORA_ROOT", str(Path(__file__).parents[2])))
WAD = 10 ** 18

app = FastAPI(title="AGORA Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── In-memory cache ────────────────────────────────────────────────────────────
_cache = {
    "stats":      {},
    "markets":    [],
    "agents":     [],
    "governance": [],
    "last_updated": 0,
}
_cache_lock = threading.Lock()

# ── Setup helpers ──────────────────────────────────────────────────────────────

def get_w3():
    return Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))

def load_abi(name):
    with open(ROOT / "config" / "abis" / f"{name}.json") as f:
        return json.load(f)

def load_addresses():
    with open(ROOT / "config" / "addresses.json") as f:
        return json.load(f)

def get_db():
    db_path = os.environ.get("DB_PATH", str(ROOT / "data" / "agora.db"))
    return sqlite3.connect(db_path)

def _addr(key_name):
    k = os.environ.get(key_name, "")
    return Account.from_key(k).address if k else None

AGENT_ADDRS = {a: n for a, n in [
    (_addr("AGENT_A_PRIVATE_KEY"), "Agent-A"),
    (_addr("AGENT_B_PRIVATE_KEY"), "Agent-B"),
    (_addr("AGENT_C_PRIVATE_KEY"), "Agent-C"),
] if a is not None}
AGENT_MODELS   = {"Agent-A": "GPT-4o #2", "Agent-B": "GPT-4o #1", "Agent-C": "DeepSeek"}

# Only show markets created on/after this date (filter out old bad markets)
# May 11 2026 00:00 UTC = 1747008000
MARKET_CUTOFF_TS = 1747054800  # May 11 2026 09:00 UTC

# Keywords that indicate a low-quality/past market
_BAD_MARKET_KEYWORDS = [
    # All of 2024
    "2024",
    # All of 2025
    "2025",
    # Already-passed months in 2026 (today is May 12 2026)
    "january 2026", "february 2026", "march 2026", "april 2026",
    # May 2026 dates that have passed
    "may 1, 2026", "may 2, 2026", "may 3, 2026", "may 4, 2026",
    "may 5, 2026", "may 6, 2026", "may 7, 2026", "may 8, 2026",
    "may 9, 2026", "may 10, 2026", "may 11, 2026",
    # Generic past patterns
    "before the end of q1", "before q2",
]

def _is_good_market(question: str, resolution_ts: int = 0, state: int = 0) -> bool:
    """Filter out low-quality or past markets."""
    import time
    q = question.lower()
    # Filter by bad keywords
    if any(kw in q for kw in _BAD_MARKET_KEYWORDS):
        return False
    # Filter ACTIVE markets that have already expired (unresolved stale markets)
    if state == 0 and resolution_ts > 0 and resolution_ts < time.time():
        return False
    return True
AGENT_PERSONAS = {"Agent-A": "Base-rate forecaster", "Agent-B": "Narrative analyst", "Agent-C": "Contrarian trader"}

# ── Cache refresh (runs in background thread every 30s) ────────────────────────

def _refresh_cache():
    try:
        w3    = get_w3()
        addrs = load_addresses()
        db    = get_db()

        factory = w3.eth.contract(
            address=Web3.to_checksum_address(addrs["MarketFactory"]),
            abi=load_abi("MarketFactory"),
        )
        governance = w3.eth.contract(
            address=Web3.to_checksum_address(addrs["Governance"]),
            abi=load_abi("Governance"),
        )
        collateral = w3.eth.contract(
            address=Web3.to_checksum_address(addrs["MockCollateral"]),
            abi=load_abi("MockCollateral"),
        )
        market_abi = load_abi("LMSRMarket")

        # ── Markets (only show recent ones, filter old bad markets) ──────────
        market_addresses = factory.functions.getAllMarkets().call()
        markets = []
        for addr in market_addresses:
            try:
                m    = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=market_abi)
                info = m.functions.getMarketInfo().call()
                # Filter out low-quality and past-event markets
                if not _is_good_market(info[0], info[2], info[9]):
                    continue
                markets.append({
                    "address":            addr,
                    "question":           info[0],
                    "resolution_criteria":info[1],
                    "resolution_timestamp":info[2],
                    "resolver":           info[3],
                    "yes_price":          round(info[4] / WAD, 4),
                    "no_price":           round(info[5] / WAD, 4),
                    "q_yes":              round(info[6] / WAD, 2),
                    "q_no":               round(info[7] / WAD, 2),
                    "b":                  round(info[8] / WAD, 2),
                    "state":              "ACTIVE" if info[9] == 0 else "RESOLVED",
                    "resolved_outcome":   ["YES","NO"][info[10]] if info[9] == 1 else None,
                    "collateral_balance": round(info[11] / WAD, 2),
                })
            except Exception:
                continue

        # ── Stats ─────────────────────────────────────────────────────────────
        trades    = db.execute("SELECT COUNT(*) FROM agent_actions WHERE action_type NOT LIKE 'hold%'").fetchone()[0]
        proposals = governance.functions.getProposalCount().call()
        stats = {
            "total_markets":    len(markets),
            "total_trades":     trades,
            "total_proposals":  proposals,
            "registered_agents":3,
            "block":            w3.eth.block_number,
            "network":          "Base Sepolia",
        }

        # ── Agents (fast: only ETH/AGORA balance + SQLite stats, no per-market RPC) ──
        agents = []
        for addr, name in AGENT_ADDRS.items():
            eth_bal = round(float(w3.from_wei(w3.eth.get_balance(addr), "ether")), 6)
            col_bal = round(collateral.functions.balanceOf(addr).call() / WAD, 2)

            # Trade stats from SQLite — instant
            st = db.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN action_type LIKE '%YES%' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN action_type LIKE '%NO%'  THEN 1 ELSE 0 END),
                       AVG(probability_estimate)
                FROM agent_actions WHERE agent_id=? AND action_type NOT LIKE 'hold%'
            """, (name,)).fetchone()

            # Derive positions from trade history (no RPC needed)
            pos_rows = db.execute("""
                SELECT market_id,
                  SUM(CASE WHEN action_type='buy_YES' THEN amount_tokens ELSE 0 END) -
                  SUM(CASE WHEN action_type='sell_YES' THEN amount_tokens ELSE 0 END) as yes_net,
                  SUM(CASE WHEN action_type='buy_NO' THEN amount_tokens ELSE 0 END) -
                  SUM(CASE WHEN action_type='sell_NO' THEN amount_tokens ELSE 0 END) as no_net
                FROM agent_actions
                WHERE agent_id=? AND action_type NOT LIKE 'hold%'
                GROUP BY market_id
                HAVING yes_net > 0 OR no_net > 0
            """, (name,)).fetchall()

            # Enrich with market questions from cache
            mkt_map = {m["address"]: m for m in markets}
            positions = []
            for mid, ynet, nnet in pos_rows:
                mkt = mkt_map.get(mid, {})
                if (ynet or 0) > 0 or (nnet or 0) > 0:
                    positions.append({
                        "market_address": mid,
                        "question":       mkt.get("question", mid[:20]+"...")[:60],
                        "yes_tokens":     round(ynet or 0, 2),
                        "no_tokens":      round(nnet or 0, 2),
                        "yes_price":      mkt.get("yes_price", 0.5),
                    })

            agents.append({
                "id": name, "address": addr,
                "model": AGENT_MODELS[name], "persona": AGENT_PERSONAS[name],
                "eth_balance":   eth_bal,
                "agora_balance": col_bal,
                "total_trades":  st[0] or 0,
                "yes_trades":    st[1] or 0,
                "no_trades":     st[2] or 0,
                "avg_prob":      round(st[3] or 0.5, 3),
                "positions":     positions,
            })

        # ── Governance: only fetch the most recent 20 proposals ──────────────
        count = governance.functions.getProposalCount().call()
        gov_list = []
        start = max(0, count - 20)
        for i in range(start, count):
            p  = governance.functions.proposals(i).call()
            vr = governance.functions.getVoteRecords(i).call()
            gov_list.append({
                "id": i,
                "proposer":            AGENT_ADDRS.get(p[0], p[0][:10]+"..."),
                "question":            p[1],
                "resolution_criteria": p[2],
                "resolution_timestamp":p[3],
                "votes_for":           p[5],
                "votes_against":       p[6],
                "voting_deadline":     p[7],
                "executed":            p[8],
                "created_market":      p[9] if p[9] != "0x"+"0"*40 else None,
                "proposer_reasoning":  p[10],
                "vote_records": [{
                    "voter":     AGENT_ADDRS.get(v[0], v[0][:10]+"..."),
                    "support":   v[1],
                    "reasoning": v[2],
                } for v in vr],
            })

        db.close()

        with _cache_lock:
            _cache["stats"]        = stats
            _cache["markets"]      = markets
            _cache["agents"]       = agents
            _cache["governance"]   = list(reversed(gov_list))
            _cache["last_updated"] = time.time()

        print(f"[cache] refreshed — {len(markets)} markets, {stats['total_trades']} trades")

    except Exception as e:
        print(f"[cache] refresh error: {e}")


def _background_refresh(interval=30):
    while True:
        _refresh_cache()
        time.sleep(interval)


@app.on_event("startup")
async def startup():
    t = threading.Thread(target=_background_refresh, daemon=True)
    t.start()

# ── API Routes (all served from cache) ────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    with _cache_lock:
        return _cache["stats"] or {"message": "Loading..."}

@app.get("/api/markets")
def get_markets():
    with _cache_lock:
        return _cache["markets"]

@app.get("/api/markets/{address}")
def get_market(address: str):
    with _cache_lock:
        for m in _cache["markets"]:
            if m["address"].lower() == address.lower():
                return m
    return {}

@app.get("/api/agents")
def get_agents():
    with _cache_lock:
        return _cache["agents"]

@app.get("/api/trades")
def get_trades(limit: int = 50):
    db   = get_db()
    rows = db.execute("""
        SELECT timestamp, agent_id, llm_backend, action_type, market_id,
               probability_estimate, confidence, reasoning,
               amount_tokens, price_before, price_after, tx_hash
        FROM agent_actions ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    return [{
        "timestamp": r[0], "agent_id": r[1], "llm_backend": r[2],
        "action_type": r[3], "market_id": r[4],
        "probability_estimate": r[5], "confidence": r[6], "reasoning": r[7],
        "amount_tokens": r[8], "price_before": r[9], "price_after": r[10],
        "tx_hash": r[11],
    } for r in rows]

@app.get("/api/markets/{address}/trades")
def get_market_trades(address: str, limit: int = 50):
    db   = get_db()
    rows = db.execute("""
        SELECT timestamp, agent_id, action_type,
               amount_tokens, price_before, price_after, tx_hash, reasoning
        FROM agent_actions
        WHERE LOWER(market_id) = LOWER(?) AND action_type NOT LIKE 'hold%'
        ORDER BY timestamp DESC LIMIT ?
    """, (address, limit)).fetchall()
    db.close()
    return [{
        "timestamp": r[0], "agent_id": r[1], "action_type": r[2],
        "amount_tokens": r[3], "price_before": r[4], "price_after": r[5],
        "tx_hash": r[6], "reasoning": r[7],
    } for r in rows]


@app.get("/api/markets/{address}/positions")
def get_market_positions(address: str):
    db   = get_db()
    rows = db.execute("""
        SELECT agent_id,
            SUM(CASE WHEN action_type='buy_YES'  THEN amount_tokens ELSE 0 END) -
            SUM(CASE WHEN action_type='sell_YES' THEN amount_tokens ELSE 0 END) as yes_net,
            SUM(CASE WHEN action_type='buy_NO'   THEN amount_tokens ELSE 0 END) -
            SUM(CASE WHEN action_type='sell_NO'  THEN amount_tokens ELSE 0 END) as no_net
        FROM agent_actions
        WHERE LOWER(market_id) = LOWER(?) AND action_type NOT LIKE 'hold%'
        GROUP BY agent_id
    """, (address,)).fetchall()
    db.close()
    return [{"agent_id": r[0], "yes_tokens": round(r[1] or 0, 2), "no_tokens": round(r[2] or 0, 2)} for r in rows]


@app.get("/api/governance")
def get_governance():
    with _cache_lock:
        return _cache["governance"]

@app.get("/api/ohlc")
def get_ohlc(market_id: str, interval: int = 300):
    db = get_db()

    # Use agent_actions price data as source (available immediately)
    rows = db.execute("""
        SELECT timestamp, price_before, price_after
        FROM agent_actions
        WHERE LOWER(market_id) = LOWER(?) AND price_before IS NOT NULL
        ORDER BY timestamp ASC
    """, (market_id,)).fetchall()

    # Also include market_prices snapshots if available
    price_rows = db.execute("""
        SELECT timestamp, agora_yes_price FROM market_prices
        WHERE LOWER(market_id) = LOWER(?) ORDER BY timestamp ASC
    """, (market_id,)).fetchall()
    db.close()

    # Merge into unified price series: (timestamp, price)
    series = []
    for ts, pb, pa in rows:
        series.append((ts - 1, pb))   # price before trade
        series.append((ts,     pa))   # price after trade
    for ts, price in price_rows:
        series.append((ts, price))
    series.sort(key=lambda x: x[0])

    if not series:
        return []

    # Aggregate into OHLC candles
    candles = []
    bucket_start = int(series[0][0] // interval) * interval
    o = h = l = c = series[0][1]

    for ts, price in series[1:]:
        bucket = int(ts // interval) * interval
        if bucket > bucket_start:
            candles.append({"t": bucket_start*1000, "o": round(o,4), "h": round(h,4), "l": round(l,4), "c": round(c,4)})
            bucket_start = bucket
            o = h = l = c = price
        else:
            h = max(h, price)
            l = min(l, price)
            c = price

    candles.append({"t": bucket_start*1000, "o": round(o,4), "h": round(h,4), "l": round(l,4), "c": round(c,4)})
    return candles

@app.get("/api/cache-status")
def cache_status():
    with _cache_lock:
        return {
            "last_updated": _cache["last_updated"],
            "age_seconds":  round(time.time() - _cache["last_updated"], 1),
            "markets":      len(_cache["markets"]),
            "agents":       len(_cache["agents"]),
        }


# ── One-time DB migration endpoint (protected by secret token) ────────────────
import base64, shutil

@app.post("/api/admin/upload-db")
async def upload_db(payload: dict):
    token = os.environ.get("ADMIN_TOKEN", "")
    if not token or payload.get("token") != token:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    db_path = os.environ.get("DB_PATH", str(ROOT / "data" / "agora.db"))
    data = base64.b64decode(payload["data"])
    tmp = db_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    shutil.move(tmp, db_path)
    return {"ok": True, "size": len(data)}


# ── Serve built frontend (must be last, catches all non-API routes) ────────────
_DIST = Path(__file__).parents[1] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
