"""
AGORA Dashboard Backend
FastAPI server that reads on-chain data and SQLite logs.
"""
import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

ROOT = Path(__file__).parents[2]
WAD = 10 ** 18

app = FastAPI(title="AGORA Dashboard API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Setup ─────────────────────────────────────────────────────────────────────

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

AGENT_NAMES = {
    Account.from_key(os.environ["AGENT_A_PRIVATE_KEY"]).address: "Agent-A",
    Account.from_key(os.environ["AGENT_B_PRIVATE_KEY"]).address: "Agent-B",
    Account.from_key(os.environ["AGENT_C_PRIVATE_KEY"]).address: "Agent-C",
}
AGENT_MODELS = {
    "Agent-A": "Claude Opus",
    "Agent-B": "GPT-4o",
    "Agent-C": "DeepSeek",
}
AGENT_PERSONAS = {
    "Agent-A": "Base-rate forecaster",
    "Agent-B": "Narrative analyst",
    "Agent-C": "Contrarian trader",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_market_info(w3, market_address, addrs):
    market = w3.eth.contract(
        address=Web3.to_checksum_address(market_address),
        abi=load_abi("LMSRMarket"),
    )
    info = market.functions.getMarketInfo().call()
    return {
        "address": market_address,
        "question": info[0],
        "resolution_criteria": info[1],
        "resolution_timestamp": info[2],
        "resolver": info[3],
        "yes_price": round(info[4] / WAD, 4),
        "no_price": round(info[5] / WAD, 4),
        "q_yes": round(info[6] / WAD, 2),
        "q_no": round(info[7] / WAD, 2),
        "b": round(info[8] / WAD, 2),
        "state": "ACTIVE" if info[9] == 0 else "RESOLVED",
        "resolved_outcome": ["YES", "NO"][info[10]] if info[9] == 1 else None,
        "collateral_balance": round(info[11] / WAD, 2),
    }

# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    w3 = get_w3()
    addrs = load_addresses()
    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    governance = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["Governance"]),
        abi=load_abi("Governance"),
    )
    db = get_db()
    trades = db.execute("SELECT COUNT(*) FROM agent_actions WHERE action_type NOT LIKE 'hold%'").fetchone()[0]
    proposals = governance.functions.getProposalCount().call()
    markets = factory.functions.getMarketCount().call()
    db.close()

    return {
        "total_markets": markets,
        "total_trades": trades,
        "total_proposals": proposals,
        "registered_agents": 3,
        "block": w3.eth.block_number,
        "network": "Base Sepolia",
    }


@app.get("/api/markets")
def get_markets():
    w3 = get_w3()
    addrs = load_addresses()
    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    market_addresses = factory.functions.getAllMarkets().call()
    markets = []
    for addr in market_addresses:
        try:
            markets.append(get_market_info(w3, addr, addrs))
        except Exception:
            continue
    return markets


@app.get("/api/markets/{address}")
def get_market(address: str):
    w3 = get_w3()
    addrs = load_addresses()
    info = get_market_info(w3, address, addrs)

    # Price history from DB
    db = get_db()
    prices = db.execute("""
        SELECT timestamp, agora_yes_price
        FROM market_prices
        WHERE market_id = ?
        ORDER BY timestamp DESC LIMIT 100
    """, (address,)).fetchall()
    db.close()

    info["price_history"] = [
        {"t": round(p[0]), "yes": round(p[1], 4)} for p in reversed(prices)
    ]
    return info


@app.get("/api/agents")
def get_agents():
    w3 = get_w3()
    addrs = load_addresses()
    collateral = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MockCollateral"]),
        abi=load_abi("MockCollateral"),
    )
    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    market_addresses = factory.functions.getAllMarkets().call()

    db = get_db()
    agents = []
    for addr, name in AGENT_NAMES.items():
        eth_bal = round(float(w3.from_wei(w3.eth.get_balance(addr), "ether")), 6)
        col_bal = round(collateral.functions.balanceOf(addr).call() / WAD, 2)

        # Positions across all markets
        positions = []
        for maddr in market_addresses:
            try:
                market = w3.eth.contract(
                    address=Web3.to_checksum_address(maddr),
                    abi=load_abi("LMSRMarket"),
                )
                info = market.functions.getMarketInfo().call()
                yes_tok = w3.eth.contract(
                    address=Web3.to_checksum_address(market.functions.yesToken().call()),
                    abi=load_abi("OutcomeToken"),
                )
                no_tok = w3.eth.contract(
                    address=Web3.to_checksum_address(market.functions.noToken().call()),
                    abi=load_abi("OutcomeToken"),
                )
                yes_bal = yes_tok.functions.balanceOf(addr).call() / WAD
                no_bal = no_tok.functions.balanceOf(addr).call() / WAD
                if yes_bal > 0 or no_bal > 0:
                    positions.append({
                        "market_address": maddr,
                        "question": info[0][:60],
                        "yes_tokens": round(yes_bal, 2),
                        "no_tokens": round(no_bal, 2),
                        "yes_price": round(info[4] / WAD, 4),
                    })
            except Exception:
                continue

        # Trade stats from DB
        stats = db.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN action_type LIKE '%YES%' THEN 1 ELSE 0 END) as yes_trades,
                SUM(CASE WHEN action_type LIKE '%NO%' THEN 1 ELSE 0 END) as no_trades
            FROM agent_actions
            WHERE agent_id = ? AND action_type NOT LIKE 'hold%'
        """, (name,)).fetchone()

        agents.append({
            "id": name,
            "address": addr,
            "model": AGENT_MODELS[name],
            "persona": AGENT_PERSONAS[name],
            "eth_balance": eth_bal,
            "agora_balance": col_bal,
            "total_trades": stats[0] or 0,
            "yes_trades": stats[1] or 0,
            "no_trades": stats[2] or 0,
            "positions": positions,
        })

    db.close()
    return agents


@app.get("/api/trades")
def get_trades(limit: int = 50):
    db = get_db()
    rows = db.execute("""
        SELECT timestamp, agent_id, llm_backend, action_type, market_id,
               probability_estimate, confidence, reasoning,
               amount_tokens, price_before, price_after, tx_hash
        FROM agent_actions
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    db.close()
    return [
        {
            "timestamp": r[0],
            "agent_id": r[1],
            "llm_backend": r[2],
            "action_type": r[3],
            "market_id": r[4],
            "probability_estimate": r[5],
            "confidence": r[6],
            "reasoning": r[7],
            "amount_tokens": r[8],
            "price_before": r[9],
            "price_after": r[10],
            "tx_hash": r[11],
        }
        for r in rows
    ]


@app.get("/api/governance")
def get_governance():
    w3 = get_w3()
    addrs = load_addresses()
    governance = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["Governance"]),
        abi=load_abi("Governance"),
    )
    count = governance.functions.getProposalCount().call()
    proposals = []
    for i in range(count):
        p = governance.functions.proposals(i).call()
        vote_records = governance.functions.getVoteRecords(i).call()
        proposals.append({
            "id": i,
            "proposer": AGENT_NAMES.get(p[0], p[0][:10] + "..."),
            "question": p[1],
            "resolution_criteria": p[2],
            "resolution_timestamp": p[3],
            "votes_for": p[5],
            "votes_against": p[6],
            "voting_deadline": p[7],
            "executed": p[8],
            "created_market": p[9] if p[9] != "0x0000000000000000000000000000000000000000" else None,
            "proposer_reasoning": p[10],
            "vote_records": [
                {
                    "voter": AGENT_NAMES.get(v[0], v[0][:10] + "..."),
                    "support": v[1],
                    "reasoning": v[2],
                }
                for v in vote_records
            ],
        })
    return list(reversed(proposals))


@app.get("/api/price-history")
def get_price_history(market_id: str, points: int = 50):
    db = get_db()
    rows = db.execute("""
        SELECT timestamp, agora_yes_price, polymarket_yes_price
        FROM market_prices
        WHERE market_id = ?
        ORDER BY timestamp DESC LIMIT ?
    """, (market_id, points)).fetchall()
    db.close()
    return [{"t": r[0], "agora": r[1], "polymarket": r[2]} for r in reversed(rows)]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
