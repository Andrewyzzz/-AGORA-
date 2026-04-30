"""
BaseAgent — the core agent loop for AGORA.

Each agent has:
  - A dedicated wallet
  - A data module (news ingestion)
  - A decision module (LLM-backed)
  - An execution module (on-chain contract calls)
  - A governance module (propose + vote)
  - A memory buffer (recent reasoning traces)
"""
import time
import logging
from dataclasses import dataclass, field
from web3 import Web3

from agents.core.wallet import Wallet
from agents.llm.base import LLMBackend
from agents.modules.data_module import DataModule
from agents.modules.decision_module import DecisionModule
from agents.modules.execution_module import ExecutionModule
from agents.modules.governance_module import GovernanceModule

logger = logging.getLogger(__name__)


@dataclass
class AgentMemory:
    max_size: int = 20
    traces: list[str] = field(default_factory=list)

    def add(self, trace: str):
        self.traces.append(trace)
        if len(self.traces) > self.max_size:
            self.traces.pop(0)

    def recent(self, n: int = 5) -> list[str]:
        return self.traces[-n:]


class BaseAgent:
    def __init__(
        self,
        agent_id: str,
        private_key: str,
        llm_backend: LLMBackend,
        w3: Web3,
        addresses: dict,
        newsapi_key: str | None = None,
    ):
        self.agent_id = agent_id
        self.w3 = w3

        self.wallet = Wallet(private_key, w3)
        self.data = DataModule(newsapi_key=newsapi_key)
        self.decision = DecisionModule(llm_backend)
        self.execution = ExecutionModule(self.wallet, w3, addresses)
        self.governance = GovernanceModule(
            self.decision, self.execution, self.data,
            agent_id, self._log,
        )
        self.memory = AgentMemory()

        self._log(f"Initialized | wallet={self.wallet.address} | llm={llm_backend.model_name}")

    def _log(self, msg: str):
        logger.info(msg)

    # ── Main loop step ────────────────────────────────────────────────────────

    def step(self, db_logger=None):
        """
        One agent step:
        1. Maybe propose a new market
        2. Vote on pending proposals
        3. Execute approved proposals
        4. Resolve expired markets (if this agent is the resolver)
        5. Trade on all active markets
        """
        import time
        news = self.data.get_recent_news(20)

        # 1. Governance: propose
        self.governance.maybe_propose()

        # 2. Governance: vote
        self.governance.vote_on_pending()

        # 3. Governance: execute approved
        self.governance.try_execute_approved()

        # 4. Resolve expired markets where this agent is the resolver
        markets = self.execution.get_all_markets()
        for market_addr in markets:
            self._maybe_resolve(market_addr, news)

        # 5. Trade on active markets
        for market_addr in markets:
            self._trade_on_market(market_addr, news, db_logger)

    def _maybe_resolve(self, market_address: str, news: list[str]):
        """Resolve a market if it has expired and this agent is the designated resolver."""
        import time
        try:
            info = self.execution.get_market_info(market_address)
        except Exception:
            return

        if info["state"] != 0:          # already resolved
            return
        if info["resolver"].lower() != self.wallet.address.lower():
            return                      # not our market to resolve
        if info["resolution_timestamp"] > time.time():
            return                      # not expired yet

        self._log(f"[{self.agent_id}] Market expired, resolving: '{info['question'][:50]}'")
        try:
            decision = self.decision.decide_resolution(
                question=info["question"],
                resolution_criteria=info["resolution_criteria"],
                evidence_sources=[
                    f"Current market price: YES={info['yes_price']:.1%}",
                    *news[:5],
                ],
            )
            outcome_int = 0 if decision.outcome == "YES" else 1
            result = self.execution.resolve(market_address, outcome_int)
            self._log(
                f"[{self.agent_id}] Resolved '{info['question'][:50]}' → "
                f"{decision.outcome} (confidence={decision.confidence}) "
                f"tx={result['tx_hash'][:12]}..."
            )
        except Exception as e:
            self._log(f"[{self.agent_id}] Resolution failed: {e}")

    def _trade_on_market(self, market_address: str, news: list[str], db_logger=None):
        try:
            info = self.execution.get_market_info(market_address)
        except Exception as e:
            self._log(f"[{self.agent_id}] Failed to get market info {market_address[:12]}: {e}")
            return

        if info["state"] != 0:  # Not ACTIVE
            return

        price_before = info["yes_price"]

        try:
            decision = self.decision.decide_trade(
                question=info["question"],
                resolution_criteria=info["resolution_criteria"],
                current_yes_price=info["yes_price"],
                recent_news=news,
                memory=self.memory.recent(),
            )
        except Exception as e:
            self._log(f"[{self.agent_id}] Decision failed on {market_address[:12]}: {e}")
            return

        outcome, action_type, amount = self.decision.parse_action(decision)

        memory_entry = (
            f"Market: {info['question'][:60]} | "
            f"Price: {price_before:.1%} → est: {decision.probability_estimate:.1%} | "
            f"Action: {decision.action} {amount:.1f} | "
            f"Confidence: {decision.confidence}"
        )
        self.memory.add(memory_entry)

        if action_type == "hold" or outcome is None or amount <= 0:
            self._log(f"[{self.agent_id}] HOLD on '{info['question'][:50]}'")
            if db_logger:
                db_logger.log_action(self.agent_id, self.decision.llm.model_name,
                    "hold", market_address, decision, price_before, price_before, None)
            return

        try:
            if action_type == "buy":
                result = self.execution.buy(market_address, outcome, amount)
            else:
                # Check we actually hold tokens before selling
                token = (self.execution.get_market(market_address)
                         .functions.yesToken().call() if outcome == 0
                         else self.execution.get_market(market_address)
                         .functions.noToken().call())
                from web3 import Web3
                from agents.modules.execution_module import _load_abi
                tok_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(token),
                    abi=_load_abi("OutcomeToken"),
                )
                balance = tok_contract.functions.balanceOf(self.wallet.address).call()
                if balance < int(amount * 10**18):
                    self._log(f"[{self.agent_id}] SKIP SELL — no {['YES','NO'][outcome]} tokens held")
                    return
                result = self.execution.sell(market_address, outcome, amount)

            info_after = self.execution.get_market_info(market_address)
            price_after = info_after["yes_price"]

            self._log(
                f"[{self.agent_id}] {decision.action} {amount:.1f} tokens on "
                f"'{info['question'][:50]}' | "
                f"price {price_before:.1%} → {price_after:.1%} | "
                f"tx={result['tx_hash'][:12]}..."
            )

            if db_logger:
                db_logger.log_action(
                    agent_id=self.agent_id,
                    llm_backend=self.decision.llm.model_name,
                    action_type=f"{action_type}_{['YES','NO'][outcome]}",
                    market_id=market_address,
                    decision=decision,
                    price_before=price_before,
                    price_after=price_after,
                    tx_hash=result["tx_hash"],
                )
        except Exception as e:
            self._log(f"[{self.agent_id}] Trade execution failed: {e}")
