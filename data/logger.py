"""
SQLite logger — records all agent actions for research analysis.
"""
import sqlite3
import json
import time
import os
from pathlib import Path

DEFAULT_DB = Path(__file__).parent / "agora.db"


class DBLogger:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.environ.get("DB_PATH", str(DEFAULT_DB))
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   REAL NOT NULL,
                    agent_id    TEXT NOT NULL,
                    llm_backend TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    market_id   TEXT NOT NULL,
                    probability_estimate REAL,
                    confidence  TEXT,
                    reasoning   TEXT,
                    amount_tokens REAL,
                    price_before  REAL,
                    price_after   REAL,
                    tx_hash     TEXT
                );

                CREATE TABLE IF NOT EXISTS market_prices (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       REAL NOT NULL,
                    market_id       TEXT NOT NULL,
                    agora_yes_price REAL,
                    polymarket_yes_price REAL,
                    polymarket_market_id TEXT
                );

                CREATE TABLE IF NOT EXISTS resolutions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    REAL NOT NULL,
                    market_id    TEXT NOT NULL,
                    question     TEXT,
                    resolved_outcome TEXT,
                    resolver_agent   TEXT,
                    confidence       TEXT,
                    brier_score      REAL
                );
            """)

    def log_action(self, agent_id, llm_backend, action_type, market_id,
                   decision, price_before, price_after, tx_hash):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_actions
                (timestamp, agent_id, llm_backend, action_type, market_id,
                 probability_estimate, confidence, reasoning, amount_tokens,
                 price_before, price_after, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                time.time(), agent_id, llm_backend, action_type, market_id,
                decision.probability_estimate,
                decision.confidence,
                decision.reasoning,
                decision.amount_tokens,
                price_before, price_after, tx_hash,
            ))

    def log_price(self, market_id, agora_price, polymarket_price=None, pm_market_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO market_prices
                (timestamp, market_id, agora_yes_price, polymarket_yes_price, polymarket_market_id)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), market_id, agora_price, polymarket_price, pm_market_id))

    def log_resolution(self, market_id, question, outcome, resolver_agent,
                       confidence, brier_score=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO resolutions
                (timestamp, market_id, question, resolved_outcome, resolver_agent,
                 confidence, brier_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (time.time(), market_id, question, outcome, resolver_agent,
                  confidence, brier_score))
