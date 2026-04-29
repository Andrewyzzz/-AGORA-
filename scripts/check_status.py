"""
Check deployment status: contract connectivity, agent balances, market info.

Usage:
    python3 scripts/check_status.py
"""
import os
import json
from pathlib import Path
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
WAD = 10 ** 18


def load_abi(name):
    with open(ROOT / "config" / "abis" / f"{name}.json") as f:
        return json.load(f)


def load_addresses():
    with open(ROOT / "config" / "addresses.json") as f:
        return json.load(f)


def main():
    w3 = Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))
    assert w3.is_connected()
    print(f"Chain {w3.eth.chain_id} | Block {w3.eth.block_number}\n")

    addrs = load_addresses()

    collateral = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MockCollateral"]),
        abi=load_abi("MockCollateral"),
    )
    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    governance = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["Governance"]),
        abi=load_abi("Governance"),
    )

    # Wallets
    wallets = {
        "Deployer": os.environ["PRIVATE_KEY"],
        "Agent-A":  os.environ["AGENT_A_PRIVATE_KEY"],
        "Agent-B":  os.environ["AGENT_B_PRIVATE_KEY"],
        "Agent-C":  os.environ["AGENT_C_PRIVATE_KEY"],
    }
    print("── Wallets ─────────────────────────────────")
    for name, key in wallets.items():
        acc = Account.from_key(key)
        eth_bal = w3.from_wei(w3.eth.get_balance(acc.address), "ether")
        col_bal = collateral.functions.balanceOf(acc.address).call() / WAD
        is_agent = governance.functions.isAgent(acc.address).call() if name != "Deployer" else "-"
        print(f"  {name:10} {acc.address}  ETH={eth_bal:.4f}  AGORA={col_bal:.0f}  registered={is_agent}")

    # Markets
    market_count = factory.functions.getMarketCount().call()
    print(f"\n── Markets ({market_count}) ──────────────────────────────")
    markets = factory.functions.getAllMarkets().call()
    market_abi = load_abi("LMSRMarket")
    for addr in markets:
        m = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=market_abi)
        info = m.functions.getMarketInfo().call()
        yes_price = info[4] / WAD
        state = "ACTIVE" if info[9] == 0 else "RESOLVED"
        print(f"  [{state}] {info[0][:60]}")
        print(f"          YES={yes_price:.1%}  NO={1-yes_price:.1%}  addr={addr[:20]}...")

    # Governance
    proposal_count = governance.functions.getProposalCount().call()
    agent_count = governance.functions.getAgentCount().call()
    print(f"\n── Governance ───────────────────────────────")
    print(f"  Registered agents : {agent_count}")
    print(f"  Proposals so far  : {proposal_count}")


if __name__ == "__main__":
    main()
