#!/usr/bin/env python
"""Validate and minimally fund the dedicated Base Sepolia evaluator wallet."""

from __future__ import annotations

import os
import sys

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def main() -> int:
    w3 = Web3(Web3.HTTPProvider(required("BASE_SEPOLIA_RPC_URL"), request_kwargs={"timeout": 60}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected() or w3.eth.chain_id != 84532:
        raise SystemExit("evaluator provisioning requires Base Sepolia (84532)")

    deployer = Account.from_key(required("DEPLOYER_PRIVATE_KEY"))
    evaluator = Account.from_key(required("SUCCESSION_EVALUATOR_KEY"))
    parties = {
        deployer.address.lower(),
        Account.from_key(required("SELLER_PRIVATE_KEY")).address.lower(),
        Account.from_key(required("BUYER_PRIVATE_KEY")).address.lower(),
        evaluator.address.lower(),
    }
    if len(parties) != 4:
        raise SystemExit("evaluator, deployer, seller and buyer must use distinct wallets")
    configured = os.environ.get("ARBITER_ADDRESS", evaluator.address)
    if configured.lower() != evaluator.address.lower():
        raise SystemExit("ARBITER_ADDRESS does not match SUCCESSION_EVALUATOR_KEY")

    target = w3.to_wei(os.environ.get("EVALUATOR_GAS_TARGET_ETH", "0.003"), "ether")
    balance = w3.eth.get_balance(evaluator.address)
    if balance < target:
        amount = target - balance
        tx = {
            "from": deployer.address,
            "to": evaluator.address,
            "value": amount,
            "nonce": w3.eth.get_transaction_count(deployer.address, "pending"),
            "chainId": w3.eth.chain_id,
        }
        tx["gas"] = w3.eth.estimate_gas(tx)
        tx["maxPriorityFeePerGas"] = w3.eth.max_priority_fee
        tx["maxFeePerGas"] = max(w3.eth.gas_price * 2, tx["maxPriorityFeePerGas"])
        signed = w3.eth.account.sign_transaction(tx, deployer.key)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        receipt = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(raw), timeout=300)
        if receipt["status"] != 1:
            raise SystemExit("evaluator funding transaction reverted")
        print(f"  funded evaluator {evaluator.address}: {receipt['transactionHash'].hex()}")
    else:
        print(f"  evaluator {evaluator.address} already funded")
    print("  custody: dedicated EOA, private key present only in ignored mode-600 operator environment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
