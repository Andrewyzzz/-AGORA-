"""
Create short-term prediction markets for testing the resolution flow.
All markets resolve within 24-72 hours from now.

Usage:
    cd /path/to/-AGORA-
    set -a && source .env && set +a
    python3 scripts/create_test_markets.py
"""
import os, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).parent.parent
WAD  = 10 ** 18

def load_abi(name):
    with open(ROOT / "config" / "abis" / f"{name}.json") as f:
        return json.load(f)

def load_addresses():
    with open(ROOT / "config" / "addresses.json") as f:
        return json.load(f)

def ts(hours_from_now):
    return int((datetime.now(timezone.utc) + timedelta(hours=hours_from_now)).timestamp())

MARKETS = [
    {
        "question": "Will BTC close above $95,000 USD on May 1, 2026?",
        "resolution_criteria": (
            "Resolves YES if the BTC/USD daily closing price on Coinbase on May 1, 2026 "
            "(00:00–23:59 UTC) exceeds $95,000. "
            "Source: Coinbase BTC-USD daily close. Fallback: CoinGecko daily high/low average."
        ),
        "hours": 24,
        "b": 100,
    },
    {
        "question": "Will ETH close above $1,800 USD on May 1, 2026?",
        "resolution_criteria": (
            "Resolves YES if the ETH/USD daily closing price on Coinbase on May 1, 2026 "
            "(00:00–23:59 UTC) exceeds $1,800. "
            "Source: Coinbase ETH-USD daily close."
        ),
        "hours": 24,
        "b": 100,
    },
    {
        "question": "Will BTC close above $95,000 USD on May 2, 2026?",
        "resolution_criteria": (
            "Resolves YES if the BTC/USD daily closing price on Coinbase on May 2, 2026 "
            "(00:00–23:59 UTC) exceeds $95,000. "
            "Source: Coinbase BTC-USD daily close."
        ),
        "hours": 48,
        "b": 100,
    },
    {
        "question": "Will the US Dollar Index (DXY) close above 99.0 on May 1, 2026?",
        "resolution_criteria": (
            "Resolves YES if the DXY (US Dollar Index) closing value on May 1, 2026 "
            "is above 99.00. Source: TradingView DXY daily close, or Investing.com."
        ),
        "hours": 24,
        "b": 100,
    },
    {
        "question": "Will gold (XAU/USD) close above $3,200 on May 2, 2026?",
        "resolution_criteria": (
            "Resolves YES if the XAU/USD (spot gold) closing price on May 2, 2026 "
            "exceeds $3,200 per troy ounce. "
            "Source: LBMA gold price PM fix, or Kitco spot gold."
        ),
        "hours": 48,
        "b": 100,
    },
    {
        "question": "Will BTC close above $95,000 USD on May 3, 2026?",
        "resolution_criteria": (
            "Resolves YES if the BTC/USD daily closing price on Coinbase on May 3, 2026 "
            "(00:00–23:59 UTC) exceeds $95,000. "
            "Source: Coinbase BTC-USD daily close."
        ),
        "hours": 72,
        "b": 100,
    },
]

def main():
    w3    = Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))
    addrs = load_addresses()

    # Use deployer as resolver for manually created markets
    deployer = Account.from_key(os.environ["PRIVATE_KEY"])

    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    collateral = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MockCollateral"]),
        abi=load_abi("MockCollateral"),
    )

    print(f"Deployer: {deployer.address}")
    print(f"Creating {len(MARKETS)} markets...\n")

    for m in MARKETS:
        resolution_ts = ts(m["hours"])
        b_wad = m["b"] * WAD
        resolution_dt = datetime.fromtimestamp(resolution_ts, tz=timezone.utc)

        tx = factory.functions.createMarket(
            b_wad,
            m["question"],
            m["resolution_criteria"],
            resolution_ts,
            deployer.address,   # deployer is resolver
        ).build_transaction({
            "from":     deployer.address,
            "nonce":    w3.eth.get_transaction_count(deployer.address, "pending"),
            "gas":      4_000_000,
            "gasPrice": w3.eth.gas_price,
            "chainId":  w3.eth.chain_id,
        })
        signed  = deployer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        # Get the new market address from factory
        market_count = factory.functions.getMarketCount().call()
        markets_list = factory.functions.getAllMarkets().call()
        new_addr = markets_list[-1]

        status = "✅" if receipt["status"] == 1 else "❌"
        print(f"{status} {m['question'][:60]}")
        print(f"   Resolves: {resolution_dt.strftime('%Y-%m-%d %H:%M UTC')} (+{m['hours']}h)")
        print(f"   Market:   {new_addr}")
        print(f"   tx:       {tx_hash.hex()[:20]}...")
        print()

    print(f"Done. Total markets on-chain: {factory.functions.getMarketCount().call()}")

if __name__ == "__main__":
    main()
