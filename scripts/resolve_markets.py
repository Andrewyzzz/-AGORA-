"""
Manually resolve expired markets using the deployer wallet.

Usage:
    python3 scripts/resolve_markets.py

Lists all ACTIVE markets past their resolution date,
prompts you for YES/NO, then submits the resolution on-chain.
"""
import os, json
from pathlib import Path
from datetime import datetime, timezone
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

def main():
    w3      = Web3(Web3.HTTPProvider(os.environ["BASE_SEPOLIA_RPC"]))
    addrs   = load_addresses()
    deployer = Account.from_key(os.environ["PRIVATE_KEY"])
    now      = int(datetime.now(timezone.utc).timestamp())

    factory = w3.eth.contract(
        address=Web3.to_checksum_address(addrs["MarketFactory"]),
        abi=load_abi("MarketFactory"),
    )
    market_abi = load_abi("LMSRMarket")

    markets = factory.functions.getAllMarkets().call()
    to_resolve = []

    for addr in markets:
        m    = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=market_abi)
        info = m.functions.getMarketInfo().call()
        state    = info[9]   # 0=ACTIVE 1=RESOLVED
        resolver = info[3]
        res_ts   = info[2]

        if state != 0:
            continue
        if resolver.lower() != deployer.address.lower():
            continue
        if res_ts > now:
            dt = datetime.fromtimestamp(res_ts, tz=timezone.utc)
            print(f"⏳ Not yet: '{info[0][:60]}' — resolves {dt.strftime('%m-%d %H:%M UTC')}")
            continue

        to_resolve.append((addr, info))

    if not to_resolve:
        print("\nNo expired markets ready to resolve.")
        return

    print(f"\n{'='*60}")
    print(f"Found {len(to_resolve)} expired market(s) to resolve:\n")

    for addr, info in to_resolve:
        yes_price = info[4] / WAD
        print(f"Market: {addr}")
        print(f"Q:      {info[0]}")
        print(f"Criteria: {info[1][:120]}")
        print(f"Current YES price: {yes_price:.1%}")
        print()

        while True:
            answer = input("Resolve as YES or NO? (y/n/skip): ").strip().lower()
            if answer in ("y", "yes"):
                outcome = 0
                break
            elif answer in ("n", "no"):
                outcome = 1
                break
            elif answer == "skip":
                print("Skipped.\n")
                outcome = None
                break
            else:
                print("Please enter y, n, or skip")

        if outcome is None:
            continue

        m = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=market_abi)
        tx = m.functions.resolve(outcome).build_transaction({
            "from":     deployer.address,
            "nonce":    w3.eth.get_transaction_count(deployer.address, "pending"),
            "gas":      200_000,
            "gasPrice": w3.eth.gas_price,
            "chainId":  w3.eth.chain_id,
        })
        signed  = deployer.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        status = "✅" if receipt["status"] == 1 else "❌"
        outcome_str = "YES" if outcome == 0 else "NO"
        print(f"{status} Resolved → {outcome_str} | tx: {tx_hash.hex()[:20]}...\n")

if __name__ == "__main__":
    main()
