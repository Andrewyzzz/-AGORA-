"""
Execution module — translates agent decisions into on-chain contract calls.
"""
import json
import os
from pathlib import Path
from web3 import Web3
from agents.core.wallet import Wallet

WAD = 10**18
ABI_DIR = Path(__file__).parents[2] / "config" / "abis"


def _load_abi(name: str) -> list:
    with open(ABI_DIR / f"{name}.json") as f:
        return json.load(f)


class ExecutionModule:
    def __init__(self, wallet: Wallet, w3: Web3, addresses: dict):
        self.wallet = wallet
        self.w3 = w3

        self.collateral = w3.eth.contract(
            address=Web3.to_checksum_address(addresses["MockCollateral"]),
            abi=_load_abi("MockCollateral"),
        )
        self.factory = w3.eth.contract(
            address=Web3.to_checksum_address(addresses["MarketFactory"]),
            abi=_load_abi("MarketFactory"),
        )
        self.governance = w3.eth.contract(
            address=Web3.to_checksum_address(addresses["Governance"]),
            abi=_load_abi("Governance"),
        )

    def get_market(self, address: str):
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=_load_abi("LMSRMarket"),
        )

    # ── Market info ──────────────────────────────────────────────────────────

    def get_market_info(self, market_address: str) -> dict:
        market = self.get_market(market_address)
        info = market.functions.getMarketInfo().call()
        return {
            "question": info[0],
            "resolution_criteria": info[1],
            "resolution_timestamp": info[2],
            "resolver": info[3],
            "yes_price": info[4] / WAD,
            "no_price": info[5] / WAD,
            "q_yes": info[6] / WAD,
            "q_no": info[7] / WAD,
            "b": info[8] / WAD,
            "state": info[9],           # 0=ACTIVE, 1=RESOLVED
            "resolved_outcome": info[10],
            "collateral_balance": info[11] / WAD,
        }

    def get_all_markets(self) -> list[str]:
        return self.factory.functions.getAllMarkets().call()

    # ── Approve collateral ───────────────────────────────────────────────────

    def ensure_approval(self, market_address: str, amount_wad: int):
        """Approve the market to spend collateral if allowance is insufficient."""
        allowance = self.collateral.functions.allowance(
            self.wallet.address,
            Web3.to_checksum_address(market_address),
        ).call()
        if allowance < amount_wad:
            tx = self.collateral.functions.approve(
                Web3.to_checksum_address(market_address),
                2**256 - 1,
            ).build_transaction({"from": self.wallet.address})
            tx_hash = self.wallet.sign_and_send(tx)
            self.wallet.wait_for_receipt(tx_hash)

    # ── Trading ──────────────────────────────────────────────────────────────

    def buy(self, market_address: str, outcome: int, amount_tokens: float) -> dict:
        """Buy YES (outcome=0) or NO (outcome=1) tokens."""
        amount_wad = int(amount_tokens * WAD)
        market = self.get_market(market_address)

        # Estimate cost and ensure approval (with 20% buffer for price movement)
        cost_wad = market.functions.getCost(outcome, amount_wad).call()
        self.ensure_approval(market_address, int(cost_wad * 1.2))

        tx = market.functions.buy(outcome, amount_wad).build_transaction({
            "from": self.wallet.address,
        })
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "cost_wad": cost_wad, "receipt": receipt}

    def sell(self, market_address: str, outcome: int, amount_tokens: float) -> dict:
        """Sell YES (outcome=0) or NO (outcome=1) tokens."""
        amount_wad = int(amount_tokens * WAD)
        market = self.get_market(market_address)
        tx = market.functions.sell(outcome, amount_wad).build_transaction({
            "from": self.wallet.address,
        })
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "receipt": receipt}

    def redeem(self, market_address: str) -> dict:
        market = self.get_market(market_address)
        tx = market.functions.redeem().build_transaction({
            "from": self.wallet.address,
        })
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "receipt": receipt}

    # ── Resolution ───────────────────────────────────────────────────────────

    def resolve(self, market_address: str, outcome: int) -> dict:
        """Resolve a market. Caller must be the designated resolver."""
        market = self.get_market(market_address)
        tx = market.functions.resolve(outcome).build_transaction({
            "from": self.wallet.address,
        })
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "receipt": receipt}

    # ── Governance ───────────────────────────────────────────────────────────

    def propose_market(self, question: str, resolution_criteria: str,
                       resolution_timestamp: int, liquidity_parameter: int,
                       reasoning: str) -> dict:
        b_wad = liquidity_parameter * WAD
        tx = self.governance.functions.propose(
            question,
            resolution_criteria,
            resolution_timestamp,
            b_wad,
            reasoning,
        ).build_transaction({"from": self.wallet.address})
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "receipt": receipt}

    def vote(self, proposal_id: int, support: bool, reasoning: str) -> dict:
        tx = self.governance.functions.vote(
            proposal_id, support, reasoning
        ).build_transaction({"from": self.wallet.address})
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        return {"tx_hash": tx_hash, "receipt": receipt}

    def execute_proposal(self, proposal_id: int) -> dict:
        tx = self.governance.functions.executeProposal(
            proposal_id
        ).build_transaction({"from": self.wallet.address})
        tx_hash = self.wallet.sign_and_send(tx)
        receipt = self.wallet.wait_for_receipt(tx_hash)
        # Read the created market address from proposal storage (most reliable)
        proposal = self.governance.functions.proposals(proposal_id).call()
        market_addr = proposal[9]  # createdMarket field
        return {"tx_hash": tx_hash, "receipt": receipt, "market_addr": market_addr}

    def get_proposal_count(self) -> int:
        return self.governance.functions.getProposalCount().call()
