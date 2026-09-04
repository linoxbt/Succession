#!/usr/bin/env python
"""Capture one real end-to-end run as the static artifact the hosted UI replays.

    python scripts/record_run.py

Writes ``web/public/recorded-run.json``. Every value in it is genuine output
from running the pipeline — no hand-written figures — and the root is
reproducible, because the export is deterministic.

If ``deployments/transfers.json`` exists, its settlement ledger is folded in so
the console's Transfers view shows the real Base Sepolia transactions instead of
an empty table. Rerun this whenever the pipeline changes: a stale artifact is a
recording of a system that no longer exists.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))

from succession.acp import job_history_from_memory  # noqa: E402
from succession.agent import Agent  # noqa: E402
from succession.demokeys import BUYER, SELLER  # noqa: E402
from succession.memory.sibyl import open_tenant  # noqa: E402
from succession.seal import SealRegistry, TenantSealed, guard  # noqa: E402
from succession.seed import seed_seller  # noqa: E402
from succession.settlement import LocalSettlement  # noqa: E402
from succession.transfer import execute_transfer, list_asset  # noqa: E402

LISTING, PRICE = "listing-0417", 420_000_000

PROMPTS = [
    "Hi, Northwind Mills again — are we still good on that Duluth run?",
    "Selkirk Timber here, about the standing rate.",
    "We need a reefer from Yakima to Denver again",
    "This is Acme Widgets, we've never worked together before.",
]


def main() -> int:
    work = ROOT / ".record-state"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    settlement = LocalSettlement(work / "settlement.db")
    seals = SealRegistry(work / "seals.db")

    seller = open_tenant(work / "seller.db", "tenant-seller")
    seed_seller(seller)

    # If ACP credentials are present, sync real job history in first so the
    # recording carries a genuine earnings record rather than none.
    try:
        from succession.acp import LiveACP, fetch_history, sync_job_history

        history = fetch_history(LiveACP())
        if history.registered:
            sync_job_history(seller, history)
            print(f"synced {len(history.jobs)} ACP jobs")
    except Exception as exc:  # noqa: BLE001 - absent credentials are the norm
        print(f"no ACP history ({type(exc).__name__}); recording without it")

    listed = list_asset(
        seller, settlement,
        listing_id=LISTING, agent_identity=SELLER.agent_id,
        seller_address=SELLER.address, private_key=SELLER.private_key, price=PRICE,
    )
    listing_open = settlement.get(LISTING).to_dict()
    preview = listed.preview.to_dict()

    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    listing_escrowed = settlement.get(LISTING).to_dict()

    buyer = open_tenant(work / "buyer.db", "tenant-buyer")
    outcome = execute_transfer(
        listing_id=LISTING, settlement=settlement, seals=seals,
        envelope=listed.envelope, content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
        buyer_identity=BUYER.agent_id, buyer_address=BUYER.address,
        expected_signer=SELLER.address,
    )
    if not outcome.verified:
        sys.exit(f"transfer failed: {outcome.failure_reason}")

    payload = outcome.to_dict()
    payload["certificate_text"] = outcome.certificate.to_text()

    agent = Agent(buyer)
    replies = {p: agent.respond(p).to_dict() for p in PROMPTS}

    # Actually attempt the write, rather than recording what we expect.
    guarded = guard(seller, seals)
    try:
        guarded.client.set_entity("commitment", "quote-NW-4472", {"rate": 2400})
        sys.exit("SEAL FAILED — a sealed tenant accepted a write")
    except TenantSealed as exc:
        write_attempt = {"accepted": False, "reason": str(exc)}

    seal = seals.get(seller.tenant_id)
    out = {
        "recorded_at": outcome.receipt.settled_at,
        "source": "scripts/record_run.py",
        "listing_open": listing_open,
        "listing_escrowed": listing_escrowed,
        "preview": preview,
        "outcome": payload,
        "replies": replies,
        "write_attempt": write_attempt,
        "seal": {"sealed": True, "at": seal.sealed_at},
        "acp": job_history_from_memory(buyer).to_dict(),
    }

    ledger = ROOT / "deployments" / "transfers.json"
    if ledger.exists():
        out["transfers"] = json.loads(ledger.read_text())["transfers"]
        print(f"folded in {len(out['transfers'])} on-chain transfers")

    dest = ROOT / "web" / "public" / "recorded-run.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str) + "\n")
    shutil.rmtree(work)

    print(f"wrote {dest}")
    print(f"root {payload['committed_root']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
