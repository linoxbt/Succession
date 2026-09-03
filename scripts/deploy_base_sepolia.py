#!/usr/bin/env python
"""Deploy ListingContract to Base Sepolia (or any EVM you point it at).

    export BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
    export DEPLOYER_PRIVATE_KEY=0x...
    python scripts/deploy_base_sepolia.py

Writes ``deployments/base-sepolia.json`` with every address and transaction
hash, which is what ``run_transfers.py`` and the UI read afterwards.

On the identity registry: ERC-8004 is a draft, and there is no single canonical
Identity Registry deployment to hardcode. Point ``IDENTITY_REGISTRY_ADDRESS`` at
the one you are using. Without it this deploys ``MockIdentityRegistry`` — a
plain ERC-721 with the same surface — and labels the deployment
``identity_registry_is_mock: true`` so nothing downstream can quietly claim
otherwise.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))

from succession.chain import load_artifact  # noqa: E402

CHAIN_ID = 84532

#: Circle's USDC on Base Sepolia — the same token Virtuals ACP uses for fares,
#: so a Succession sale settles in the currency the agent already earns in.
DEFAULT_PAYMENT_TOKEN = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(
            f"{name} is not set.\n"
            "  BASE_SEPOLIA_RPC_URL  an RPC endpoint (https://sepolia.base.org)\n"
            "  DEPLOYER_PRIVATE_KEY  a funded Base Sepolia key\n"
            "  Faucet: https://docs.base.org/get-started/get-funds"
        )
    return value


def deploy(w3: Web3, account, name: str, *args) -> str:
    artifact = load_artifact(name)
    factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = factory.constructor(*args).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": w3.eth.chain_id,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, account.key)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    receipt = w3.eth.wait_for_transaction_receipt(
        w3.eth.send_raw_transaction(raw), timeout=300
    )
    if receipt["status"] != 1:
        sys.exit(f"{name} deployment reverted ({receipt['transactionHash'].hex()})")
    print(f"  {name:<22} {receipt['contractAddress']}")
    return receipt["contractAddress"]


def connect_local():
    """An in-process EVM, so this script is exercised rather than merely parsed.

    ``--local`` runs the identical deployment path against py-evm: same
    artifacts, same constructor arguments, same receipt checks. It proves the
    script works before anyone spends real testnet ETH finding out it does not.
    """
    from eth_tester import EthereumTester, PyEVMBackend
    from web3 import EthereumTesterProvider

    key = os.environ.get("DEPLOYER_PRIVATE_KEY") or ("0x" + "33" * 32)
    account = Account.from_key(key)
    backend = PyEVMBackend.from_mnemonic(
        "test test test test test test test test test test test junk",
        genesis_state_overrides={"balance": Web3.to_wei(1000, "ether")},
    )
    w3 = Web3(EthereumTesterProvider(EthereumTester(backend)))
    w3.eth.send_transaction(
        {"from": w3.eth.accounts[0], "to": account.address,
         "value": w3.to_wei(100, "ether")}
    )
    return w3, account


def deploy_all(w3: Web3, account, *, local: bool = False) -> dict:
    """Deploy the contract set and return the deployment record.

    Shared with ``run_transfers.py --local``, which must deploy in its own
    process: an in-process EVM does not survive the interpreter that made it,
    so a local run cannot read a deployment file written by an earlier one.
    """
    payment_token = os.environ.get("PAYMENT_TOKEN_ADDRESS", DEFAULT_PAYMENT_TOKEN)
    registry = os.environ.get("IDENTITY_REGISTRY_ADDRESS")
    registry_is_mock = registry is None

    print("deploying:")
    if local:
        # Circle's USDC does not exist on an in-process chain.
        payment_token = deploy(w3, account, "MockERC20")
    if registry_is_mock:
        print("  (no IDENTITY_REGISTRY_ADDRESS — deploying the ERC-721 stand-in)")
        registry = deploy(w3, account, "MockIdentityRegistry")

    arbiter = os.environ.get("ARBITER_ADDRESS", account.address)
    listings = deploy(w3, account, "ListingContract", payment_token, registry, arbiter)

    return {
        "network": "local" if local else "base-sepolia",
        "chain_id": w3.eth.chain_id,
        "listing_contract": listings,
        "identity_registry": registry,
        "identity_registry_is_mock": registry_is_mock,
        "payment_token": payment_token,
        "arbiter": arbiter,
        "deployer": account.address,
        # No explorer for an in-process chain: a Basescan link to an address
        # that only ever existed in memory is a link to nothing.
        "explorer": (
            "" if local else f"https://sepolia.basescan.org/address/{listings}"
        ),
    }


def main() -> int:
    local = "--local" in sys.argv
    if local:
        w3, account = connect_local()
        print("running against an in-process EVM (--local)")
    else:
        rpc = require("BASE_SEPOLIA_RPC_URL")
        account = Account.from_key(require("DEPLOYER_PRIVATE_KEY"))

        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 60}))
        # Base is an OP-stack chain: its blocks carry extra header data that
        # web3's default validation rejects.
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not w3.is_connected():
            sys.exit(f"cannot reach {rpc}")

    chain_id = w3.eth.chain_id
    if not local and chain_id != CHAIN_ID:
        print(f"warning: connected to chain {chain_id}, not Base Sepolia ({CHAIN_ID})")

    balance = w3.eth.get_balance(account.address)
    print(f"deployer {account.address}  {w3.from_wei(balance, 'ether')} ETH")
    if balance == 0:
        sys.exit(
            "deployer has no ETH. Fund it: https://docs.base.org/get-started/get-funds"
        )

    out = deploy_all(w3, account, local=local)
    listings = out["listing_contract"]
    registry_is_mock = out["identity_registry_is_mock"]
    dest = ROOT / "deployments" / ("local.json" if local else "base-sepolia.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")

    print(f"\nwrote {dest}")
    if out["explorer"]:
        print(f"explorer: {out['explorer']}")
    if registry_is_mock:
        print(
            "\nnote: the identity registry is a stand-in, recorded as such in the "
            "deployment file. Set IDENTITY_REGISTRY_ADDRESS to use a real "
            "ERC-8004 registry."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
