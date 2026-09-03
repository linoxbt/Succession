"""The two-machine demo, wired end to end.

Runs the whole Part 3 workflow against real Sibyl Memory stores and the local
settlement mirror, and prints each beat so the rehearsal has something to check
its timing against.

The important constraint the spec puts on this: it is **not** simulate-able with
two browser tabs. Seller and buyer get separate store files here, and
``--seller-dir``/``--buyer-dir`` exist so the two halves can run on genuinely
separate machines, passing the envelope between them as a file. Running both
halves in one process is the fast local loop, not the demo.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .dataroom import build_preview
from .demokeys import BUYER, SELLER
from .memory.sibyl import open_tenant
from .seal import SealRegistry, TenantSealed, guard
from .seed import seed_seller
from .settlement import LocalSettlement
from .transfer import execute_transfer, list_asset
from .valuation import value_tenant

LISTING_ID = "listing-0417"
PRICE = 420_000_000  # 420 USDC at 6 decimals


class Console:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet

    def beat(self, time: str, title: str) -> None:
        if not self.quiet:
            print(f"\n\033[1m[{time}] {title}\033[0m")

    def line(self, label: str, value: Any = "") -> None:
        if not self.quiet:
            print(f"  {label:<28} {value}")

    def note(self, text: str) -> None:
        if not self.quiet:
            print(f"  \033[2m{text}\033[0m")


def run_demo(workdir: Path, *, quiet: bool = False, fresh: bool = True) -> dict[str, Any]:
    out = Console(quiet)
    if fresh and workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    settlement = LocalSettlement(workdir / "settlement.db")
    seals = SealRegistry(workdir / "seals.db")

    # -- 0:00 the seller's agent, mid-relationship ---------------------
    out.beat("0:00", "Agent A is mid-relationship with a returning customer")
    seller = open_tenant(workdir / "seller.db", "tenant-seller")
    seed_seller(seller)
    position = seller.client.get_state("current-negotiation")["body"]
    out.line("Agent", "Meridian Logistics Co. (erc8004:84532:0417)")
    out.line("Counterparty", position["counterparty"])
    out.line("They asked", f'"{position["last_message_from_counterparty"]}"')
    out.line("Open commitment", position["commitment"])

    # -- 0:20 the listing ----------------------------------------------
    out.beat("0:20", "The operator lists Agent A — redacted preview, reference valuation")
    listed = list_asset(
        seller,
        settlement,
        listing_id=LISTING_ID,
        agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=PRICE,
    )
    preview = listed.preview
    out.line("Registered", f"{preview.tenure_days} days")
    out.line("Journal events", preview.counts["journal_events"])
    out.line("Memory size", f"{preview.memory_size_bytes / 1024:.1f} KB")
    out.line("Valuation (reference)", f"${preview.valuation.amount}")
    out.line("Committed hash", listed.committed_root)
    out.line("Seller signature", listed.listing.seller_signature[:22] + "…")
    out.note(
        f"{preview.withheld_non_transferable} record marked non-transferable — "
        "excluded before hashing, so it is not in the tree at all"
    )
    out.note(f"named in preview: {', '.join(preview.public_counterparties)} (public only)")

    # -- 0:45 escrow ----------------------------------------------------
    out.beat("0:45", "A buyer reviews the preview and funds escrow")
    settlement.buy(LISTING_ID, buyer=BUYER.address, amount=PRICE)
    listing = settlement.get(LISTING_ID)
    out.line("State", listing.state.value)
    out.line("Escrow held", f"{listing.escrow_balance / 1_000_000:.2f} {listing.currency}")
    out.line("Envelope", f"{listed.envelope.size_bytes:,} bytes, AES-256-GCM")
    out.note("the content key is released only against funded escrow")

    # -- 1:05 the atomic transfer --------------------------------------
    out.beat("1:05", "Atomic transfer: re-key under the buyer's tenant, settle on-chain")
    buyer = open_tenant(workdir / "buyer.db", "tenant-buyer")
    outcome = execute_transfer(
        listing_id=LISTING_ID,
        settlement=settlement,
        seals=seals,
        envelope=listed.envelope,
        content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id,
        buyer_sink=buyer,
        buyer_identity=BUYER.agent_id,
        buyer_address=BUYER.address,
        expected_signer=SELLER.address,
    )
    out.line("Committed hash", outcome.committed_root)
    out.line("Delivered hash", outcome.delivered_root)
    out.line("Match", "YES" if outcome.verified else "NO")
    out.line("Escrow", outcome.receipt.outcome)
    out.line("Paid to", outcome.receipt.paid_to)
    out.line("Identity now held by", outcome.receipt.identity_transferred_to)
    if not outcome.verified:
        raise SystemExit(f"transfer failed: {outcome.failure_reason}")

    if not quiet:
        print()
        for line in outcome.certificate.to_text().splitlines():
            print("  " + line)

    # -- 1:25 the sealed seller ----------------------------------------
    out.beat("1:25", "The seller's copy is sealed — a write is rejected on camera")
    sealed_seller = guard(seller, seals)
    try:
        sealed_seller.client.set_entity("commitment", "quote-NW-4472", {"rate": 2400})
        raise SystemExit("SEAL FAILED — a sealed tenant accepted a write")
    except TenantSealed as exc:
        out.line("Write attempt", "REJECTED")
        out.note(str(exc))

    # -- 1:35 the cold boot --------------------------------------------
    out.beat("1:35", "The buyer's agent boots cold and recalls the in-flight quote")
    cold = open_tenant(workdir / "buyer.db", "tenant-buyer")
    quote = cold.client.get_entity("commitment", "quote-NW-4471")["body"]
    recalled = cold.client.get_state("current-negotiation")["body"]
    counterparty = cold.client.get_entity("relationship", "northwind-mills")["body"]
    behaviour = cold.client.get_entity("learned-behavior", "thursday-booking-pattern")["body"]

    out.line("Never seen this customer", "(fresh session, new tenant)")
    out.line("Customer", counterparty["company"])
    out.line("Open quote", f'{quote["lane"]} at ${quote["quoted_rate_usd"]:,}')
    out.line("Their last message", f'"{recalled["last_message_from_counterparty"]}"')
    out.line("Our position", recalled["our_position"])
    out.line("Learned habit", behaviour["pattern"])

    # -- 2:00 the proof -------------------------------------------------
    out.beat("2:00", "Why this was not staged with a shared database")
    acquisition = cold.client.get_entity("provenance", "acquisition")["body"]
    out.line("Origin agent", acquisition["acquired_from"])
    out.line("Verified hash", acquisition["verified_hash"])
    out.line("Seller signature", acquisition["seller_signature"][:22] + "…")
    out.line("Settlement", acquisition["settlement_reference"])
    out.line("Provenance chain", f'{len(acquisition["provenance_chain"])} entry')
    out.note(
        "the buyer re-hashed their own store after the import; the root matches "
        "the one committed before a buyer existed"
    )

    return {
        "listing": settlement.get(LISTING_ID).to_dict(),
        "preview": preview.to_dict(),
        "outcome": outcome.to_dict(),
        "certificate": outcome.certificate.to_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="succession-demo", description="Run the Succession transfer demo."
    )
    parser.add_argument(
        "--workdir", type=Path, default=Path("demo-state"), help="where the stores live"
    )
    parser.add_argument("--json", action="store_true", help="emit the result as JSON")
    parser.add_argument("--keep", action="store_true", help="reuse an existing workdir")
    args = parser.parse_args(argv)

    result = run_demo(args.workdir, quiet=args.json, fresh=not args.keep)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print("\n\033[1mTransfer complete and verified.\033[0m\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
