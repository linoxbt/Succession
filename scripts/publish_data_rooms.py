#!/usr/bin/env python
"""Publish the data room for each listing that already settled on chain.

    export SELLER_PRIVATE_KEY=0x...
    python scripts/publish_data_rooms.py

The five transfers in ``deployments/transfers.json`` were made on chain and
never described. That is why the dashboard reports zero of six sellers with a
data room, and why every directory in the capability table reads zero: the
counts come from what sellers published, and nobody published.

This closes that gap without inventing anything. Each preview is computed from
the seller tenant the sale actually drew on, so the numbers on screen are the
memory that changed hands rather than a plausible-looking fixture. A listing
whose store is missing is skipped and reported, not filled in.

Authentication is the seller's own signature over the listing id. The service
checks it against the address the *contract* records as seller, so this cannot
describe a listing the key does not own.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))

from succession.dataroom import build_preview  # noqa: E402
from succession.memory.sibyl import open_tenant  # noqa: E402
from succession.publish import seller_auth_header  # noqa: E402

DEFAULT_SERVICE = "https://marketplace-production-e49e.up.railway.app"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--service", default=os.environ.get("SUCCESSION_SERVICE", DEFAULT_SERVICE))
    ap.add_argument("--runs", type=Path, default=ROOT / "transfer-runs")
    ap.add_argument("--transfers", type=Path, default=ROOT / "deployments" / "transfers.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    key = os.environ.get("SELLER_PRIVATE_KEY")
    if not key and not args.dry_run:
        sys.exit("SELLER_PRIVATE_KEY is not set")

    record = json.loads(args.transfers.read_text())
    contract = record["contract"]
    chain_id = int(record.get("chain_id", 84532))

    published = skipped = failed = 0
    for entry in record["transfers"]:
        listing_id = entry["listing_id"]
        index = entry["index"]
        store = args.runs / f"seller-{index}.db"
        if not store.exists():
            print(f"  skip  {listing_id}: no store at {store}")
            skipped += 1
            continue

        source = open_tenant(store, f"tenant-seller-{index}")
        preview = build_preview(
            source,
            agent_identity=entry["agent_id"],
            committed_root=entry["committed_root"],
        )
        body = {
            "listing_id": listing_id,
            "agent_identity": entry["agent_id"],
            # The contract's own commitment. The service rejects the post if
            # this disagrees with what it reads on chain, which is the check
            # that stops metadata describing a sale that never happened.
            "committed_root": entry["committed_root"],
            "chain_id": chain_id,
            "contract": contract,
            "name": f"Agent {entry['agent_id'].rsplit(':', 1)[-1]}",
            "vertical": "Freight brokerage",
            "valuation": str(preview.valuation.get("reference", "")) if isinstance(
                preview.valuation, dict
            ) else str(preview.valuation or ""),
            "preview": preview.to_dict(),
        }

        if args.dry_run:
            t = preview.to_dict().get("category_transferability", {})
            sellable = sum(v.get("sellable", 0) for v in t.values())
            print(f"  would  {listing_id}: {sellable} sellable records across {len(t)} directories")
            published += 1
            continue

        response = requests.post(
            f"{args.service}/api/listings",
            json=body,
            headers=seller_auth_header(key, listing_id),
            timeout=60,
        )
        if response.status_code == 200:
            print(f"  ok    {listing_id}")
            published += 1
        else:
            print(f"  FAIL  {listing_id}: {response.status_code} {response.text[:160]}")
            failed += 1

    print(f"\npublished {published}, skipped {skipped}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
