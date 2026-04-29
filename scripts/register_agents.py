"""
Register the three agent wallets with the Governance contract.
Must be run once after deployment, using the deployer wallet (admin).

Usage:
    cd /path/to/-AGORA-
    python3 scripts/register_agents.py
"""
import os
import sys
import json
from pathlib import Path
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
ABI_DIR = ROOT / "config" / "abis"


def load_abi(name: str) -> list:
    with open(ABI_DIR / f"{name}.json") as f:
        return json.load(f)


def load_addresses() -> dict:
    with open(ROOT / "config" / "addresses.json") as f:
        return json.load(f)


def main():
    rpc = os.environ["BASE_SEPOLIA_RPC"]
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), "Cannot connect to RPC"

    deployer_key = os.environ["PRIVATE_KEY"]
    deployer = Account.from_key(deployer_key)
    print(f"Deployer: {deployer.address}")

    addresses = load_addresses()
    governance = w3.eth.contract(
        address=Web3.to_checksum_address(addresses["Governance"]),
        abi=load_abi("Governance"),
    )

    agent_keys = {
        "Agent-A": os.environ["AGENT_A_PRIVATE_KEY"],
        "Agent-B": os.environ["AGENT_B_PRIVATE_KEY"],
        "Agent-C": os.environ["AGENT_C_PRIVATE_KEY"],
    }

    for name, key in agent_keys.items():
        agent_addr = Account.from_key(key).address

        # Check if already registered
        if governance.functions.isAgent(agent_addr).call():
            print(f"✓ {name} ({agent_addr}) already registered")
            continue

        # Register
        tx = governance.functions.registerAgent(agent_addr).build_transaction({
            "from": deployer.address,
            "nonce": w3.eth.get_transaction_count(deployer.address, "pending"),
            "gas": 100000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        })
        signed = deployer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        status = "✅" if receipt["status"] == 1 else "❌"
        print(f"{status} Registered {name} ({agent_addr}) — tx: {tx_hash.hex()[:20]}...")

    # Verify final count
    count = governance.functions.getAgentCount().call()
    agents = governance.functions.getAllAgents().call()
    print(f"\nTotal registered agents: {count}")
    for a in agents:
        print(f"  {a}")


if __name__ == "__main__":
    main()
