"""
AGORA — main orchestrator.

Spawns three AI agents with different LLM backends and runs the autonomous
prediction market lifecycle: propose → vote → trade → resolve.

Usage:
    cp .env.example .env  # fill in your API keys and private keys
    pip install -r requirements.txt
    python main.py
"""
import os
import json
import time
import logging
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv
from rich.logging import RichHandler
from rich.console import Console

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
log = logging.getLogger("agora")
console = Console()

from agents.core.base_agent import BaseAgent
from agents.llm.claude_backend import ClaudeBackend
from agents.llm.openai_backend import OpenAIBackend
from agents.llm.deepseek_backend import DeepSeekBackend
from agents.prompts.base_rate_agent import SYSTEM_PROMPT as PROMPT_A
from agents.prompts.narrative_agent import SYSTEM_PROMPT as PROMPT_B
from agents.prompts.contrarian_agent import SYSTEM_PROMPT as PROMPT_C
from data.logger import DBLogger

CONFIG_DIR = Path("config")


def load_addresses() -> dict:
    with open(CONFIG_DIR / "addresses.json") as f:
        addrs = json.load(f)
    required = ["MockCollateral", "MarketFactory", "Governance"]
    missing = [k for k in required if not addrs.get(k)]
    if missing:
        raise ValueError(
            f"Contract addresses not set: {missing}\n"
            f"Run: forge script contracts/script/Deploy.s.sol "
            f"--rpc-url $BASE_SEPOLIA_RPC --broadcast\n"
            f"Then update config/addresses.json"
        )
    return addrs


def build_agents(w3: Web3, addresses: dict) -> list[BaseAgent]:
    newsapi_key = os.environ.get("NEWSAPI_KEY")
    agents = []

    # Agent A — Claude — Base-rate forecaster
    key_a = os.environ.get("AGENT_A_PRIVATE_KEY")
    if key_a:
        agents.append(BaseAgent(
            agent_id="Agent-A",
            private_key=key_a,
            llm_backend=ClaudeBackend(system_prompt=PROMPT_A),
            w3=w3,
            addresses=addresses,
            newsapi_key=newsapi_key,
        ))

    # Agent B — GPT-4 — Narrative analyst
    key_b = os.environ.get("AGENT_B_PRIVATE_KEY")
    if key_b:
        agents.append(BaseAgent(
            agent_id="Agent-B",
            private_key=key_b,
            llm_backend=OpenAIBackend(system_prompt=PROMPT_B),
            w3=w3,
            addresses=addresses,
            newsapi_key=newsapi_key,
        ))

    # Agent C — DeepSeek — Contrarian trader
    key_c = os.environ.get("AGENT_C_PRIVATE_KEY")
    if key_c:
        agents.append(BaseAgent(
            agent_id="Agent-C",
            private_key=key_c,
            llm_backend=DeepSeekBackend(system_prompt=PROMPT_C),
            w3=w3,
            addresses=addresses,
            newsapi_key=newsapi_key,
        ))

    if not agents:
        raise ValueError("No agent private keys found. Set AGENT_A_PRIVATE_KEY etc. in .env")

    return agents


def main():
    console.rule("[bold cyan]AGORA — Autonomous AI Prediction Markets[/bold cyan]")

    rpc = os.environ.get("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), f"Cannot connect to RPC: {rpc}"
    log.info(f"Connected to chain {w3.eth.chain_id} (block {w3.eth.block_number})")

    addresses = load_addresses()
    log.info(f"Contracts loaded from config/addresses.json")

    agents = build_agents(w3, addresses)
    db = DBLogger()
    log.info(f"Running {len(agents)} agent(s): {[a.agent_id for a in agents]}")

    step_interval = int(os.environ.get("STEP_INTERVAL_SECONDS", "300"))  # 5 min default

    console.rule("[green]Starting agent loop[/green]")
    step_count = 0
    while True:
        step_count += 1
        console.rule(f"Step {step_count}")
        for agent in agents:
            try:
                agent.step(db_logger=db)
            except Exception as e:
                log.error(f"[{agent.agent_id}] Step failed: {e}", exc_info=True)

        # Log price snapshot for every active market after each step
        try:
            from web3 import Web3 as _W3
            import json as _json
            _w3 = _W3(_W3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))
            _addrs = json.load(open(Path("config/addresses.json")))
            _factory_abi = json.load(open(Path("config/abis/MarketFactory.json")))
            _market_abi  = json.load(open(Path("config/abis/LMSRMarket.json")))
            _factory = _w3.eth.contract(
                address=_W3.to_checksum_address(_addrs["MarketFactory"]),
                abi=_factory_abi,
            )
            WAD = 10 ** 18
            for maddr in _factory.functions.getAllMarkets().call():
                try:
                    _m = _w3.eth.contract(address=_W3.to_checksum_address(maddr), abi=_market_abi)
                    info = _m.functions.getMarketInfo().call()
                    if info[9] == 0:  # ACTIVE only
                        db.log_price(maddr, info[4] / WAD)
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"Price logging failed: {e}")

        log.info(f"Step {step_count} complete. Sleeping {step_interval}s...")
        time.sleep(step_interval)


if __name__ == "__main__":
    main()
