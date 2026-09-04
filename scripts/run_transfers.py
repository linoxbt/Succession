#!/usr/bin/env python
"""Run N real memory transfers against a deployed ListingContract.

    export BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
    export SELLER_PRIVATE_KEY=0x...   # holds the ERC-8004 identities, funded
    export BUYER_PRIVATE_KEY=0x...    # funded, and holding the payment token
    python scripts/run_transfers.py --count 5

Each run is a genuinely separate sale: its own agent identity, its own seeded
seller tenant, its own empty buyer tenant, its own listing, escrow, delivery,
re-hash and settlement. Nothing is reused between them, because five sales of
one asset would only prove the contract can be called five times.

Writes ``deployments/transfers.json`` — every transaction hash, both roots, and
the certificate — which is what the UI and the README's evidence table read.

One transfer is deliberately corrupted (``--corrupt N``) unless you turn it off.
Five successes prove the happy path works; they say nothing about whether the
refund path does, and the refund is the half that protects the buyer.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from succession.chain import ChainSettlement
from succession.erc8004 import (
    AgentRegistration,
    IdentityRegistry,
    agent_identity,
)  # noqa: E402
from succession.envelope import seal_package  # noqa: E402
from succession.memory.sibyl import open_tenant  # noqa: E402
from succession.seal import SealRegistry  # noqa: E402
from succession.seed import seed_seller  # noqa: E402
from succession.transfer import execute_transfer, list_asset  # noqa: E402

PRICE = 1_000_000  # 1 USDC at 6 decimals — testnet, keep it cheap


def env(name: str) -> str:
    import os

    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set")
    return value


def connect(local: bool) -> Web3:
    if local:
        from eth_tester import EthereumTester, PyEVMBackend
        from web3 import EthereumTesterProvider

        backend = PyEVMBackend.from_mnemonic(
            "test test test test test test test test test test test junk",
            genesis_state_overrides={"balance": Web3.to_wei(1000, "ether")},
        )
        return Web3(EthereumTesterProvider(EthereumTester(backend)))

    w3 = Web3(Web3.HTTPProvider(env("BASE_SEPOLIA_RPC_URL"), request_kwargs={"timeout": 60}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        sys.exit("cannot reach the RPC endpoint")
    return w3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--corrupt",
        type=int,
        default=3,
        help="1-based index of the transfer to corrupt, proving the refund path; 0 disables",
    )
    parser.add_argument("--first-token-id", type=int, default=901)
    parser.add_argument("--workdir", type=Path, default=ROOT / "transfer-runs")
    parser.add_argument(
        "--local", action="store_true",
        help="run against an in-process EVM, to exercise this script without testnet ETH",
    )
    args = parser.parse_args()

    w3 = connect(args.local)

    if args.local:
        import os

        os.environ.setdefault("SELLER_PRIVATE_KEY", "0x" + "11" * 32)
        os.environ.setdefault("BUYER_PRIVATE_KEY", "0x" + "22" * 32)
        # An in-process EVM dies with the process that made it, so a local run
        # deploys its own contracts rather than reading an earlier run's file.
        from deploy_base_sepolia import deploy_all

        deployer = Account.from_key(os.environ.get("DEPLOYER_PRIVATE_KEY", "0x" + "33" * 32))
        w3.eth.send_transaction(
            {"from": w3.eth.accounts[0], "to": deployer.address,
             "value": w3.to_wei(100, "ether")}
        )
        deployment = deploy_all(w3, deployer, local=True)
    else:
        deployment = json.loads(
            (ROOT / "deployments" / "base-sepolia.json").read_text()
        )

    seller_key, buyer_key = env("SELLER_PRIVATE_KEY"), env("BUYER_PRIVATE_KEY")
    seller_addr = Account.from_key(seller_key).address
    buyer_addr = Account.from_key(buyer_key).address

    settlement = ChainSettlement(
        w3,
        contract_address=deployment["listing_contract"],
        seller_key=seller_key,
        buyer_key=buyer_key,
    )

    registry = IdentityRegistry(w3, address=deployment["identity_registry"])

    if args.workdir.exists():
        shutil.rmtree(args.workdir)
    args.workdir.mkdir(parents=True)

    if args.local:
        # Fund and stock the two identities on the in-process chain.
        token = w3.eth.contract(
            address=Web3.to_checksum_address(deployment["payment_token"]),
            abi=[
                {"name": "mint", "type": "function", "stateMutability": "nonpayable",
                 "inputs": [{"name": "to", "type": "address"},
                            {"name": "amount", "type": "uint256"}], "outputs": []},
            ],
        )
        for who in (seller_addr, buyer_addr):
            w3.eth.send_transaction(
                {"from": w3.eth.accounts[0], "to": who, "value": w3.to_wei(50, "ether")}
            )
        token.functions.mint(buyer_addr, PRICE * (args.count + 5)).transact(
            {"from": w3.eth.accounts[0]}
        )

    # Approve once for the whole run rather than per sale.
    settlement.approve_payment(
        deployment["payment_token"], buyer_addr, PRICE * (args.count + 2)
    )

    results = []
    for i in range(1, args.count + 1):
        corrupt = i == args.corrupt

        # Each sale gets its own identity, minted for real. ERC-8004
        # registration is permissionless, so the seller mints its own agent
        # rather than being handed a token id it does not own — which is what
        # the previous mock-only path silently assumed, and what would have
        # failed on the first real run against a public registry.
        token_id = registry.register(
            AgentRegistration(
                name=f"Succession origin agent {i}",
                description=(
                    "A seeded freight-brokerage memory, listed for transfer "
                    "through Succession."
                ),
                wallet=seller_addr,
            ),
            seller_key,
        )
        # The successor is its own registered agent, not a reused id. The
        # certificate names an origin and a successor, and a run where those
        # two were the same identity would be recording a sale to oneself.
        successor_token = registry.register(
            AgentRegistration(
                name=f"Succession successor agent {i}",
                description="The acquiring agent, booted against the transferred memory.",
                wallet=buyer_addr,
            ),
            buyer_key,
        )
        agent_id = agent_identity(deployment["chain_id"], token_id)
        successor_id = agent_identity(deployment["chain_id"], successor_token)
        listing_id = f"listing-{token_id}"
        print(f"\n[{i}/{args.count}] {agent_id}{'  (corrupted on purpose)' if corrupt else ''}")

        registry.approve(deployment["listing_contract"], token_id, seller_key)

        seller = open_tenant(args.workdir / f"seller-{i}.db", f"tenant-seller-{i}")
        seed_seller(seller, agent_identity=agent_id)
        buyer = open_tenant(args.workdir / f"buyer-{i}.db", f"tenant-buyer-{i}")

        listed = list_asset(
            seller, settlement,
            listing_id=listing_id, agent_identity=agent_id,
            seller_address=seller_addr, private_key=seller_key, price=PRICE,
        )
        print(f"  committed root {listed.committed_root}")

        settlement.buy(listing_id, buyer=buyer_addr, amount=PRICE)
        print("  escrow funded")

        envelope = listed.envelope
        if corrupt:
            tampered = copy.deepcopy(listed.export.package)
            tampered.data["preferences"][0]["body"]["floor_pct"] = 0
            envelope, _ = seal_package(
                tampered, listing_id=listing_id,
                hash_commitment=listed.committed_root, key=listed.content_key,
            )

        outcome = execute_transfer(
            listing_id=listing_id, settlement=settlement,
            seals=SealRegistry(args.workdir / "seals.db"),
            envelope=envelope, content_key=listed.content_key,
            seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
            buyer_identity=successor_id,
            buyer_address=buyer_addr, expected_signer=seller_addr,
        )

        tx = outcome.receipt.reference if outcome.receipt else ""
        # A Basescan link for a chain that only existed in memory points at
        # nothing, so local runs print the hash alone.
        explorer = "" if args.local else f"https://sepolia.basescan.org/tx/{tx}"
        print(f"  {outcome.outcome}  tx {tx}")
        if explorer:
            print(f"  {explorer}")

        results.append({
            "index": i,
            "agent_id": agent_id,
            "listing_id": listing_id,
            "intentionally_corrupted": corrupt,
            "outcome": outcome.outcome,
            "committed_root": outcome.committed_root,
            "delivered_root": outcome.delivered_root,
            "tx": tx,
            "explorer": explorer,
            "certificate": outcome.certificate.to_dict() if outcome.certificate else None,
        })

        expected = "refunded" if corrupt else "verified"
        if outcome.outcome != expected:
            sys.exit(f"transfer {i} was {outcome.outcome}, expected {expected}")

    dest = ROOT / "deployments" / ("transfers-local.json" if args.local else "transfers.json")
    dest.write_text(json.dumps(
        {"network": deployment["network"], "contract": deployment["listing_contract"],
         "transfers": results}, indent=2) + "\n")

    verified = sum(1 for r in results if r["outcome"] == "verified")
    print(f"\n{verified} verified, {len(results) - verified} refunded (as designed)")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
