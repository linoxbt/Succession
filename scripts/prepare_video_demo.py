#!/usr/bin/env python
"""Register a fresh Base Sepolia origin/successor pair for a filmed demo.

The origin receives a seeded local Sibyl tenant. The successor and evaluator
stores are created empty. No listing or sale is started, so the printed pair is
ready for the operator to run through the normal CLI workflow on camera.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))

from succession.erc8004 import AgentRegistration, IdentityRegistry, agent_identity, registration_uri
from succession.memory.sibyl import open_tenant
from succession.seed import seed_seller


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def register(registry: IdentityRegistry, registration: AgentRegistration, key: str) -> tuple[int, str]:
    receipt = registry._send(registry.contract.functions.register(registration_uri(registration)), key)
    return registry._agent_id_from(receipt), Web3.to_hex(receipt["transactionHash"])


def main() -> int:
    deployment = json.loads((ROOT / "deployments" / "base-sepolia.json").read_text())
    w3 = Web3(Web3.HTTPProvider(required("BASE_SEPOLIA_RPC_URL"), request_kwargs={"timeout": 60}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected() or w3.eth.chain_id != 84532:
        raise SystemExit("Base Sepolia RPC is unavailable or on the wrong chain")

    seller_key, buyer_key = required("SELLER_PRIVATE_KEY"), required("BUYER_PRIVATE_KEY")
    seller, buyer = Account.from_key(seller_key).address, Account.from_key(buyer_key).address
    registry = IdentityRegistry(w3, address=deployment["identity_registry"])

    origin_name = "Succession video origin"
    successor_name = "Succession video successor"
    origin, origin_tx = register(registry, AgentRegistration(
        name=origin_name,
        description="A freight-brokerage agent whose signed memory package is ready for a Succession demo.",
        wallet=seller,
    ), seller_key)
    successor, successor_tx = register(registry, AgentRegistration(
        name=successor_name,
        description="The acquiring agent prepared to receive and verify transferred memory.",
        wallet=buyer,
    ), buyer_key)

    origin_identity = agent_identity(deployment["chain_id"], origin)
    successor_identity = agent_identity(deployment["chain_id"], successor)
    workdir = ROOT / "video-demo-ready"
    workdir.mkdir(exist_ok=False)
    seller_store = open_tenant(workdir / "seller.db", "video-seller")
    seed_seller(seller_store, agent_identity=origin_identity)
    open_tenant(workdir / "buyer.db", "video-successor")
    open_tenant(workdir / "evaluator.db", "video-evaluator")

    record = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "network": "base-sepolia", "chain_id": 84532,
        "contract": deployment["listing_contract"], "registry": deployment["identity_registry"],
        "origin": {"name": origin_name, "identity": origin_identity, "token_id": origin, "owner": seller, "registration_tx": origin_tx},
        "successor": {"name": successor_name, "identity": successor_identity, "token_id": successor, "owner": buyer, "registration_tx": successor_tx},
        "listing_id": f"listing-{origin}", "price_minor_units": 1_000_000,
        "stores": {"seller": "video-demo-ready/seller.db", "buyer": "video-demo-ready/buyer.db", "evaluator": "video-demo-ready/evaluator.db"},
        "tenants": {"seller": "video-seller", "buyer": "video-successor", "evaluator": "video-evaluator"},
        "status": "ready-unlisted",
    }
    destination = ROOT / "deployments" / "demo-video-ready.json"
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    print(f"wrote {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
