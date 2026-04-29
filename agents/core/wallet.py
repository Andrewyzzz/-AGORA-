"""
Wallet management for AGORA agents.
Each agent has a dedicated Ethereum wallet (private key + address).
"""
from web3 import Web3
from eth_account import Account


class Wallet:
    def __init__(self, private_key: str, w3: Web3):
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.w3 = w3
        self._nonce_lock = 0

    @property
    def balance_eth(self) -> float:
        return self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")

    def get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(self.address, "pending")

    def sign_and_send(self, tx: dict) -> str:
        """Sign a transaction dict and broadcast it. Returns tx hash."""
        tx.setdefault("nonce", self.get_nonce())
        tx.setdefault("chainId", self.w3.eth.chain_id)
        if "gas" not in tx:
            tx["gas"] = self.w3.eth.estimate_gas(tx)
        if "gasPrice" not in tx and "maxFeePerGas" not in tx:
            tx["gasPrice"] = self.w3.eth.gas_price

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> dict:
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    def __repr__(self):
        return f"Wallet({self.address[:10]}...)"
