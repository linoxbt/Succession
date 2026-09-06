"""The seller's and buyer's HTTP client for a marketplace.

Three commands talk to a marketplace and each one used to hand-roll `urllib`
inline, which is how two of them ended up not talking to it at all: `list`
never uploaded the encrypted package, and `fulfil` never delivered the content
key. Both reported success. Putting the calls in one module makes the set of
things that cross the wire something you can read in one place and count.

`urllib` rather than `requests` on purpose. The package's install footprint is
its own argument — a seller installing this to sell one agent's memory should
not acquire a dependency tree for four HTTP calls.

Nothing here is authoritative. The marketplace is an index and a relay: it
holds ciphertext, aggregate counts, and a key it will not serve until the
contract says escrow is funded. Every claim it makes is re-checked against the
chain by the code that reads it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .publish import seller_auth_header

__all__ = ["MarketplaceError", "get", "post", "publish_metadata", "deliver_key"]

TIMEOUT = 30


class MarketplaceError(RuntimeError):
    """A marketplace call did not succeed.

    Carries the status where there was one, so a caller can tell "the listing
    is not published" (404) from "you are not its seller" (403) from "the host
    is unreachable" without parsing a message.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def get(base: str, path: str) -> Any:
    """Read from the marketplace, raising `MarketplaceError` rather than HTTPError."""
    try:
        with urllib.request.urlopen(_url(base, path), timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise MarketplaceError(
            f"{path} returned {exc.code}: "
            f"{exc.read().decode('utf-8', 'replace')[:200]}",
            status=exc.code,
        ) from exc
    except OSError as exc:
        raise MarketplaceError(f"could not reach {base}: {exc}") from exc


def post(base: str, path: str, body: dict[str, Any], *, private_key: str, listing_id: str) -> Any:
    """Write to the marketplace as the listing's seller.

    Authentication is a signature over the listing id, not an account: the
    seller already holds the key the contract recorded, so nothing else needs
    inventing. The service recovers the address and checks it against the chain
    rather than against anything it stores.
    """
    request = urllib.request.Request(
        _url(base, path),
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            **seller_auth_header(private_key, listing_id),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise MarketplaceError(
            f"{path} was refused with {exc.code}: "
            f"{exc.read().decode('utf-8', 'replace')[:200]}",
            status=exc.code,
        ) from exc
    except OSError as exc:
        raise MarketplaceError(f"could not reach {base}: {exc}") from exc


def publish_metadata(
    base: str,
    stored: Any,
    *,
    envelope: Any,
    preview: dict[str, Any] | None = None,
    integrity: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    private_key: str,
) -> Any:
    """Publish what the contract has no field for, including the ciphertext.

    The envelope belongs here rather than in the seller's vault alone. It is
    AES-256-GCM and inert without the content key, so serving it before payment
    costs nothing, and holding it means a buyer can fetch the bytes the moment
    escrow lands instead of waiting on the seller's connection for those as well
    as for the key.

    Leaving it out was a real outage: `claim` fetches `/envelope` first, so a
    buyer who had already paid got a 404 and had nothing to decrypt.

    Takes the pieces rather than a listing-time object so the same call serves
    both `succession list`, which has a fresh export in hand, and
    `succession publish`, which reconstructs them from the vault after a
    marketplace was unreachable.
    """
    body: dict[str, Any] = {
        "listing_id": stored.listing_id,
        "agent_identity": stored.agent_identity,
        "committed_root": stored.committed_root,
        "chain_id": int(stored.chain_id),
        "contract": stored.listing_contract,
        "name": stored.agent_identity,
        "vertical": "",
        "valuation": stored.valuation_reference,
        "preview": preview if preview is not None else dict(stored.preview or {}),
        "envelope": envelope.to_dict(),
    }
    # Roots, counts, category names and a signature. No record body, which is
    # why these are safe to publish before anyone has paid, and publishing them
    # is what lets a buyer check the sale rather than take it on trust.
    if integrity:
        body["integrity"] = integrity
    if provenance:
        body["provenance"] = provenance

    return post(
        base, "/api/listings", body,
        private_key=private_key, listing_id=stored.listing_id,
    )


def deliver_key(base: str, listing_id: str, content_key: bytes, *, private_key: str) -> Any:
    """Hand a released content key to the marketplace for the buyer to collect.

    Safe to send because both ends check the same thing: the service re-reads
    the contract before accepting the key and again before serving it, and the
    caller has already confirmed on chain that escrow is funded and that the
    commitment matches what was listed.
    """
    return post(
        base, f"/api/listing/{listing_id}/key",
        {"content_key": content_key.hex()},
        private_key=private_key, listing_id=listing_id,
    )
