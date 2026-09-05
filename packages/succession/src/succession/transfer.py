"""The orchestrator: Part 3's end-to-end workflow, as one auditable call.

:func:`list_asset` covers steps 2-3 (package, sign, list). :func:`execute_transfer`
covers steps 6-12 (escrow confirmation through the post-sale record), and it is
written so that every early return leaves the world in a state someone can
explain:

* **Bad delivery.** Verification fails before a row is written, the buyer's
  tenant is purged of anything a partial write left, escrow refunds, the
  seller's tenant is *not* sealed, and the seller keeps operating. Nobody has
  lost anything but time.
* **Settlement refuses.** Same compensating purge, same refund. The seller is
  unsealed because the sale did not happen.
* **Success.** Payment released, identity moved, and the seal follows — in that
  order, because sealing a seller whose payment then failed to release would be
  the single worst outcome the system can produce.

The seal is deliberately the *last* step, and it is deliberately not conditional
on anything that can still fail after it. By the time it runs, the money and the
identity have already moved together in one on-chain transaction; sealing is
recording a fact, not taking a risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from .certificate import SuccessionCertificate
from .dataroom import DataRoomPreview, build_preview
from .envelope import SealedEnvelope, open_envelope, seal_package
from .export import ExportResult, export_tenant
from .importer import IntegrityMismatch, import_package
from .provenance import append_owner, utc_now
from .seal import SealRecord, SealRegistry
from .settlement import Listing, ListingState, SettlementError, SettlementReceipt
from .smp import SMPPackage
from .valuation import value_tenant

__all__ = ["ListedAsset", "TransferOutcome", "list_asset", "execute_transfer"]


@dataclass
class ListedAsset:
    """Everything produced at listing time."""

    listing: Listing
    export: ExportResult
    preview: DataRoomPreview
    envelope: SealedEnvelope
    content_key: bytes = field(repr=False)

    @property
    def committed_root(self) -> str:
        return self.export.root_hex


@dataclass
class TransferOutcome:
    listing_id: str
    outcome: str                                   # "verified" | "refunded"
    receipt: SettlementReceipt | None = None
    import_result: Any = None
    certificate: SuccessionCertificate | None = None
    seal_record: SealRecord | None = None
    committed_root: str = ""
    delivered_root: str = ""
    failure_reason: str = ""

    @property
    def verified(self) -> bool:
        return self.outcome == "verified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "outcome": self.outcome,
            "committed_root": self.committed_root,
            "delivered_root": self.delivered_root,
            "failure_reason": self.failure_reason,
            "receipt": self.receipt.to_dict() if self.receipt else None,
            "certificate": self.certificate.to_dict() if self.certificate else None,
            "seal": self.seal_record.to_dict() if self.seal_record else None,
        }


def list_asset(
    seller: Any,
    settlement: Any,
    *,
    listing_id: str,
    agent_identity: str,
    seller_address: str,
    private_key: str,
    price: int,
    currency: str = "USDC",
    categories: Sequence[str] | None = None,
    base_price: Decimal | str | int | None = None,
    provenance_chain: list[dict[str, Any]] | None = None,
) -> ListedAsset:
    """Steps 2-3: build and sign the package, then post the commitment.

    The package is built *once*, here, and the envelope handed to the buyer is
    encryption of that same object. Rebuilding it at delivery time would be the
    subtle way to make the commitment meaningless — the seller could commit to
    one memory and ship another that happened to hash the same way only because
    nobody re-checked.
    """
    export = export_tenant(
        seller,
        agent_identity=agent_identity,
        private_key=private_key,
        categories=categories,
        provenance_chain=provenance_chain,
    )
    valuation = (
        value_tenant(seller, base_price=base_price)
        if base_price is not None
        else value_tenant(seller)
    )
    preview = build_preview(
        seller,
        agent_identity=agent_identity,
        committed_root=export.root_hex,
        base_price=base_price,
    )
    listing = settlement.list_asset(
        listing_id=listing_id,
        agent_id=agent_identity,
        seller=seller_address,
        seller_signature=export.package.header["signature"],
        hash_commitment=export.root_hex,
        price=price,
        currency=currency,
        categories=tuple(export.package.categories),
        valuation_reference=str(valuation.to_dict()["amount"]),
    )
    envelope, key = seal_package(
        export.package,
        listing_id=listing_id,
        hash_commitment=export.root_hex,
    )
    return ListedAsset(
        listing=listing,
        export=export,
        preview=preview,
        envelope=envelope,
        content_key=key,
    )


def execute_transfer(
    *,
    listing_id: str,
    settlement: Any,
    seals: SealRegistry,
    envelope: SealedEnvelope,
    content_key: bytes,
    seller_tenant_id: str,
    buyer_sink: Any,
    buyer_identity: str,
    buyer_address: str,
    expected_signer: str,
) -> TransferOutcome:
    """Steps 6-12: decrypt, import, verify, settle, seal, record."""
    listing = settlement.get(listing_id)
    if listing.state is not ListingState.ESCROWED:
        raise SettlementError(
            f"listing {listing_id!r} is {listing.state.value}; the content key is "
            "released only against funded escrow"
        )

    committed = listing.hash_commitment
    package = open_envelope(envelope, content_key)

    # -- step 7-8: deliver, re-key, verify -----------------------------
    try:
        import_result = import_package(
            package,
            buyer_sink,
            committed_root=committed,
            expected_signer=expected_signer,
        )
    except Exception as exc:
        delivered = getattr(exc, "delivered", "")
        buyer_sink.purge()
        receipt = settlement.refund(
            listing_id, reason=str(exc), delivered_hash=delivered
        )
        return TransferOutcome(
            listing_id=listing_id,
            outcome="refunded",
            receipt=receipt,
            committed_root=committed,
            delivered_root=delivered,
            failure_reason=str(exc),
        )

    # -- step 7 (chain leg): payment + identity + sealed flag, atomically
    receipt = settlement.confirm_transfer(
        listing_id,
        delivered_hash=import_result.reimported_root,
        buyer_identity=buyer_identity,
    )
    if receipt.outcome != "released":
        buyer_sink.purge()
        return TransferOutcome(
            listing_id=listing_id,
            outcome="refunded",
            receipt=receipt,
            committed_root=committed,
            delivered_root=import_result.reimported_root,
            failure_reason="settlement declined to release escrow",
        )

    # -- step 9: seal the seller's copy ---------------------------------
    seal_record = seals.seal(
        seller_tenant_id,
        reason=f"memory asset sold under listing {listing_id}",
        agent_identity=listing.agent_id,
        transfer_id=receipt.reference,
    )

    # -- step 12: post-sale record, written into the buyer's memory -----
    _write_post_sale_record(
        buyer_sink,
        header=package.header,
        listing=listing,
        receipt=receipt,
        verified_hash=import_result.reimported_root,
        buyer_identity=buyer_identity,
    )

    # -- step 10: the certificate ---------------------------------------
    certificate = SuccessionCertificate.from_transfer(
        header=package.header,
        import_result=import_result,
        transfer_date=receipt.settled_at,
        successor_agent=buyer_identity,
        seal_record=seal_record,
        settlement_reference=receipt.reference,
    )

    return TransferOutcome(
        listing_id=listing_id,
        outcome="verified",
        receipt=receipt,
        import_result=import_result,
        certificate=certificate,
        seal_record=seal_record,
        committed_root=committed,
        delivered_root=import_result.reimported_root,
    )


def _write_post_sale_record(
    buyer_sink: Any,
    *,
    header: dict[str, Any],
    listing: Listing,
    receipt: SettlementReceipt,
    verified_hash: str,
    buyer_identity: str,
) -> None:
    """Step 12: the acquisition becomes part of the buyer's own memory.

    A WARM ``provenance/acquisition`` entity plus a COLD journal line. Together
    they are what the buyer's *next* export reads to extend the provenance
    chain, which is why no separate lineage store is needed: the record of how
    the memory was acquired lives inside the memory.
    """
    chain = append_owner(
        header,
        owner=buyer_identity,
        verified_hash=verified_hash,
        acquired_at=receipt.settled_at,
        memory_version=header["memory_version"],
    )
    buyer_sink.write_entities(
        [
            {
                "kind": "entity",
                "category": "provenance",
                "name": "acquisition",
                "status": "verified",
                "body": {
                    "acquired_from": header["agent_identity"],
                    "acquired_by": buyer_identity,
                    "listing_id": listing.listing_id,
                    "sale_date": receipt.settled_at,
                    "price": listing.price,
                    "currency": listing.currency,
                    "verified_hash": verified_hash,
                    "seller_signature": header.get("signature"),
                    "settlement_reference": receipt.reference,
                    "memory_version_at_sale": header["memory_version"],
                    "categories": header.get("categories", []),
                    "provenance_chain": chain,
                },
            }
        ]
    )
    buyer_sink.write_events(
        [
            {
                "kind": "event",
                "id": "",
                "ts": receipt.settled_at,
                "acted": [
                    f"acquired from {header['agent_identity']}, hash verified "
                    f"{verified_hash}"
                ],
                "evaluated": None,
                "forward": None,
                "extra": {"listing_id": listing.listing_id},
            }
        ]
    )
