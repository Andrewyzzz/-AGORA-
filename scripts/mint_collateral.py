"""
Mint AGORA collateral tokens to agent wallets.
MockCollateral.mint() is public on testnet — no access control.

Usage:
    python3 scripts/mint_collateral.py
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
MINT_AMOUNT = 100_000 * WAD  # 100,000 AGORA per agent


def load_abi(name):
    with open(ROOT / "config" / "abis" / f"{name}.json") as f:
        return json.load(f)


def load_addresses():
    with open(ROOT / "config" / "addresses.json") as f:
        return json.load(f)


def main():
    w3 = Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))
    assert w3.is_connected()

    deployer = Account.from_key(os.environ["PRIVATE_KEY"])
    addrs = load_addresses()

    collateral = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MockCollateral"]),
        abi=load_abi("MockCollateral"),
    )

    agents = {
        "Agent-A": Account.from_key(os.environ["AGENT_A_PRIVATE_KEY"]).address,
        "Agent-B": Account.from_key(os.environ["AGENT_B_PRIVATE_KEY"]).address,
        "Agent-C": Account.from_key(os.environ["AGENT_C_PRIVATE_KEY"]).address,
    }

    for name, addr in agents.items():
        current = collateral.functions.balanceOf(addr).call()
        if current >= MINT_AMOUNT:
            print(f"✓ {name} already has {current/WAD:.0f} AGORA, skipping")
            continue

        tx = collateral.functions.mint(addr, MINT_AMOUNT).build_transaction({
            "from": deployer.address,
            "nonce": w3.eth.get_transaction_count(deployer.address, "pending"),
            "gas": 80000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id,
        })
        signed = deployer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        status = "✅" if receipt["status"] == 1 else "❌"
        print(f"{status} Minted 100,000 AGORA to {name} ({addr}) — tx: {tx_hash.hex()[:20]}...")

    print("\nFinal balances:")
    for name, addr in agents.items():
        bal = collateral.functions.balanceOf(addr).call() / WAD
        print(f"  {name}: {bal:,.0f} AGORA")


if __name__ == "__main__":
    main()
