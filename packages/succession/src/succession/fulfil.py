"""Seller-side fulfilment: release the key, but only against escrow you can see.

The key question this module answers is *who decides that escrow is funded*.

If the marketplace held the content key and released it when it believed escrow
had landed, the escrow guarantee would be worth exactly as much as the
marketplace's honesty and uptime. So it does not hold the key. The seller does,
and this is the process that hands it over — after reading the listing's state
from the chain itself and finding it ``Escrowed``.

That makes the seller a liveness requirement: a buyer who funds escrow against a
seller who is offline waits. It is a real cost and worth stating plainly rather
than hiding, and it is bounded — ``reclaimExpired`` returns the buyer's money
after the confirmation window without needing the seller's cooperation at all.

The ciphertext is a different matter. It is AES-256-GCM sealed and useless
without the key, so it can be uploaded at listing time and served to anyone; the
buyer can have it sitting on their disk long before they pay and be no closer to
reading it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .publish import PublishError, SellerVault, StoredListing
from .settlement import ListingState, SettlementError

__all__ = [
    "DeliveryError",
    "Fulfilment",
    "FulfilmentError",
    "release_for",
    "watch",
]


class FulfilmentError(Exception):
    """A key could not be released."""


class DeliveryError(FulfilmentError):
    """The key was cleared for release but could not be handed over.

    Distinct in meaning from its parent: `FulfilmentError` says the chain does
    not permit a release, while this says the decision was right and the
    transport failed. It subclasses anyway so `watch` treats it as it treats any
    other release failure, logging and retrying on the next poll rather than
    tearing down a seller's long-running watcher over a network blip.

    Retrying is safe: nothing was consumed. The key is still in the vault and
    the contract is still the thing that decides whether it may leave.
    """


@dataclass(frozen=True)
class Fulfilment:
    """One key release."""

    listing_id: str
    buyer: str
    released: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "buyer": self.buyer,
            "released": self.released,
            "reason": self.reason,
        }


def release_for(
    listing_id: str,
    settlement: Any,
    *,
    vault: SellerVault | None = None,
    deliver: Callable[[StoredListing, bytes, str], None] | None = None,
) -> Fulfilment:
    """Release the content key for one listing, if the chain says escrow is funded.

    ``deliver`` receives ``(stored, content_key, buyer)`` and is what actually
    hands the key over — posting it to the marketplace relay, writing it to a
    file, whatever the seller wants. Keeping it injectable means this decision
    (*should* the key go out) stays separate from the transport (*how* it goes
    out), and only the decision is security-critical.
    """
    vault = vault or SellerVault()
    stored = vault.read(listing_id)

    try:
        listing = settlement.get(listing_id)
    except SettlementError as exc:
        raise FulfilmentError(f"cannot read {listing_id} from chain: {exc}") from exc

    if listing.state is ListingState.OPEN:
        return Fulfilment(listing_id, "", False, "no buyer has funded escrow yet")
    if listing.state is not ListingState.ESCROWED:
        return Fulfilment(
            listing_id, listing.buyer or "", False,
            f"listing is {listing.state.value}; nothing to release",
        )

    # Escrow is funded. Two things are still worth checking, because a listing
    # read from the wrong contract would satisfy the state test alone.
    if listing.hash_commitment.lower() != stored.committed_root.lower():
        raise FulfilmentError(
            f"{listing_id} on chain commits to {listing.hash_commitment}, but the "
            f"vault holds {stored.committed_root}. Refusing to release a key for "
            "memory that is not what was listed."
        )
    if not listing.buyer:
        raise FulfilmentError(f"{listing_id} is escrowed but names no buyer")

    key = vault.content_key(listing_id)
    if deliver is not None:
        deliver(stored, key, listing.buyer)
    return Fulfilment(listing_id, listing.buyer, True, "escrow funded on chain")


def watch(
    settlement: Any,
    *,
    vault: SellerVault | None = None,
    deliver: Callable[[StoredListing, bytes, str], None] | None = None,
    interval: int = 30,
    once: bool = False,
    listings: Iterable[str] | None = None,
    log: Callable[[str], None] = print,
) -> list[Fulfilment]:
    """Poll every listing in the vault and release keys as escrow lands.

    Polling rather than an event subscription because a missed WebSocket frame
    during a reconnect is a sale that silently never completes, while a missed
    poll is one that completes on the next tick. The interval is the seller's
    latency floor, not a correctness parameter.
    """
    vault = vault or SellerVault()
    done: set[str] = set()
    results: list[Fulfilment] = []

    while True:
        wanted = list(listings) if listings else [s.listing_id for s in vault.all()]
        for listing_id in wanted:
            if listing_id in done:
                continue
            try:
                outcome = release_for(
                    listing_id, settlement, vault=vault, deliver=deliver
                )
            except (FulfilmentError, PublishError) as exc:
                log(f"  {listing_id}: {exc}")
                continue
            if outcome.released:
                done.add(listing_id)
                results.append(outcome)
                log(f"  {listing_id}: key released to {outcome.buyer}")
            else:
                log(f"  {listing_id}: {outcome.reason}")
        if once:
            return results
        time.sleep(interval)
