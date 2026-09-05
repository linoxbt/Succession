"""Seller-side listing: put your own agent's memory up for sale, for real.

Why this module exists rather than a form in the web app
--------------------------------------------------------

Sibyl Memory 0.8.0 is local-only. ``MemoryClient.local(path)`` is its sole
constructor, and the package makes no network calls except a tier check and a
heartbeat — there is no hosted store and no account for a browser to connect to.
A seller's memory is a SQLite file on the seller's own disk, and no web page can
read it.

That constraint turns out to be the right shape anyway. The claim this project
makes is that plaintext memory never leaves the seller before escrow funds; the
only way to mean that is for the export, the encryption and the signature to
happen on the seller's machine. So listing is a local operation, and what
reaches the network is:

* the Merkle root and the signed header — public by design, committed on chain
* the *encrypted* package — useless to anyone without the content key
* aggregate preview counts — the data room, which is counts and never bodies

The content key stays in the seller's vault until they see escrow funded on
chain themselves. See :mod:`succession.fulfil`.

The vault
---------

``~/.succession/listings/<listing_id>/`` holds ``envelope.json``, ``key`` (mode
0600) and ``meta.json``. The key sits beside the ciphertext on the seller's own
disk, which is fine — it is the seller's own asset. What matters is that it does
not sit beside the ciphertext anywhere the *buyer* can reach before paying.
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from eth_account import Account
from eth_account.messages import encode_defunct

from .envelope import SealedEnvelope
from .transfer import ListedAsset, list_asset

__all__ = [
    "VAULT",
    "PublishError",
    "SellerVault",
    "StoredListing",
    "listing_id_for",
    "publish_listing",
    "seller_auth_header",
]

#: Where a seller's listings live. Overridable for tests and for anyone who
#: keeps their working files somewhere other than home.
VAULT = Path(os.environ.get("SUCCESSION_VAULT", "~/.succession/listings")).expanduser()

#: Domain tag for the signature that proves who is posting a listing's metadata.
#: Distinct from the provenance and evaluation domains so a marketplace login
#: can never be replayed as an export signature or an evaluator verdict.
AUTH_DOMAIN = "Succession/1.0/seller-auth"


class PublishError(Exception):
    """A listing could not be published."""


def listing_id_for(agent_identity: str, root_hex: str) -> str:
    """A listing id derived from what is being sold, not from a counter.

    Two sellers must never collide, and the same seller re-listing the same
    memory unchanged should be told the listing already exists rather than
    silently creating a second one. Deriving from the agent and the committed
    root gives both, and it is reproducible: a seller who loses their vault can
    recompute the id from a fresh export of unchanged memory.
    """
    from eth_utils import keccak

    digest = keccak(f"{agent_identity}|{root_hex}".encode()).hex()
    return f"listing-{digest[:24]}"


@dataclass(frozen=True)
class StoredListing:
    """What the seller keeps locally after publishing."""

    listing_id: str
    agent_identity: str
    committed_root: str
    price: int
    currency: str
    categories: tuple[str, ...]
    seller: str
    chain_id: int
    listing_contract: str
    valuation_reference: str
    preview: dict[str, Any]
    tx_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "agent_identity": self.agent_identity,
            "committed_root": self.committed_root,
            "price": self.price,
            "currency": self.currency,
            "categories": list(self.categories),
            "seller": self.seller,
            "chain_id": self.chain_id,
            "listing_contract": self.listing_contract,
            "valuation_reference": self.valuation_reference,
            "preview": self.preview,
            "tx_hash": self.tx_hash,
        }

    @classmethod
    def from_dict(cls, blob: dict[str, Any]) -> "StoredListing":
        return cls(
            listing_id=blob["listing_id"],
            agent_identity=blob["agent_identity"],
            committed_root=blob["committed_root"],
            price=int(blob["price"]),
            currency=blob.get("currency", "USDC"),
            categories=tuple(blob.get("categories", ())),
            seller=blob["seller"],
            chain_id=int(blob["chain_id"]),
            listing_contract=blob["listing_contract"],
            valuation_reference=blob.get("valuation_reference", ""),
            preview=blob.get("preview", {}),
            tx_hash=blob.get("tx_hash", ""),
        )


class SellerVault:
    """The seller's local store of what they have listed."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root).expanduser() if root else VAULT

    def path(self, listing_id: str) -> Path:
        return self.root / listing_id

    def exists(self, listing_id: str) -> bool:
        return (self.path(listing_id) / "meta.json").is_file()

    def write(
        self,
        stored: StoredListing,
        *,
        envelope: SealedEnvelope,
        content_key: bytes,
    ) -> Path:
        directory = self.path(stored.listing_id)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "meta.json").write_text(
            json.dumps(stored.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        (directory / "envelope.json").write_text(
            json.dumps(envelope.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        key_path = directory / "key"
        key_path.write_text(content_key.hex() + "\n", encoding="utf-8")
        # The one file here that is actually a secret.
        key_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return directory

    def read(self, listing_id: str) -> StoredListing:
        path = self.path(listing_id) / "meta.json"
        if not path.is_file():
            raise PublishError(f"no listing {listing_id!r} in {self.root}")
        return StoredListing.from_dict(json.loads(path.read_text("utf-8")))

    def envelope(self, listing_id: str) -> SealedEnvelope:
        path = self.path(listing_id) / "envelope.json"
        if not path.is_file():
            raise PublishError(f"no envelope for {listing_id!r}")
        return SealedEnvelope.from_dict(json.loads(path.read_text("utf-8")))

    def content_key(self, listing_id: str) -> bytes:
        path = self.path(listing_id) / "key"
        if not path.is_file():
            raise PublishError(f"no content key for {listing_id!r}")
        return bytes.fromhex(path.read_text("utf-8").strip())

    def all(self) -> list[StoredListing]:
        if not self.root.is_dir():
            return []
        out = []
        for directory in sorted(self.root.iterdir()):
            meta = directory / "meta.json"
            if meta.is_file():
                out.append(StoredListing.from_dict(json.loads(meta.read_text("utf-8"))))
        return out


def seller_auth_header(private_key: str, listing_id: str) -> dict[str, str]:
    """Prove control of the listing's seller address, without a password.

    The marketplace needs to know that whoever posts a listing's metadata is the
    address that listed it on chain. It does not need an account, a session or a
    stored credential to establish that — the seller already holds the key that
    the contract recorded, so signing the listing id with it is proof enough,
    and the service checks the recovered address against the chain rather than
    against anything it stores.
    """
    message = f"{AUTH_DOMAIN}\n{listing_id}"
    signed = Account.sign_message(encode_defunct(text=message), private_key)
    return {
        "X-Succession-Address": Account.from_key(private_key).address,
        "X-Succession-Signature": signed.signature.hex(),
    }


def recover_seller_auth(listing_id: str, signature: str) -> str:
    """The address that signed this listing id. Raises on a malformed signature."""
    message = f"{AUTH_DOMAIN}\n{listing_id}"
    return Account.recover_message(encode_defunct(text=message), signature=signature)


def publish_listing(
    memory: Any,
    settlement: Any,
    *,
    agent_identity: str,
    private_key: str,
    price: int,
    chain_id: int,
    listing_contract: str,
    categories: Sequence[str] | None = None,
    scope: Any = None,
    base_price: Decimal | str | int | None = None,
    currency: str = "USDC",
    vault: SellerVault | None = None,
) -> tuple[StoredListing, ListedAsset]:
    """Export a real store, commit it on chain, and keep the key locally.

    ``settlement`` is a :class:`~succession.settlement.SettlementBackend`. In
    production that is :class:`~succession.chain.ChainSettlement` against a
    deployed contract; the tests drive the identical path against py-evm.

    Nothing here is seeded or synthetic: the package is built from whatever the
    passed store actually contains, and the root, the preview counts and the
    valuation are computed from it.
    """
    if price <= 0:
        raise PublishError("price must be positive")

    seller_address = Account.from_key(private_key).address
    vault = vault or SellerVault()

    # Build the package first so the listing id can be derived from the
    # commitment. A pre-allocated id would let two exports of different memory
    # share one listing.
    from .export import export_tenant

    probe = export_tenant(
        memory,
        agent_identity=agent_identity,
        private_key=private_key,
        categories=categories,
        scope=scope,
    )
    listing_id = listing_id_for(agent_identity, probe.root_hex)
    if vault.exists(listing_id):
        raise PublishError(
            f"{listing_id} is already in your vault — this memory, unchanged, is "
            "already listed. Change what is for sale or cancel the existing listing."
        )

    asset = list_asset(
        memory,
        settlement,
        listing_id=listing_id,
        agent_identity=agent_identity,
        seller_address=seller_address,
        private_key=private_key,
        price=price,
        currency=currency,
        categories=categories,
        scope=scope,
        base_price=base_price,
    )

    # Computed here rather than read back off the listing. `LocalSettlement`
    # stores a valuation because it is a database; the contract has no field for
    # one and should not — it is a reference figure, not a term of the sale — so
    # reading it back from a chain listing returns an empty string. The seller
    # is the one who can compute it, and this is the record they publish.
    from .valuation import value_tenant

    valuation = (
        value_tenant(memory, base_price=base_price)
        if base_price is not None
        else value_tenant(memory)
    )

    stored = StoredListing(
        listing_id=listing_id,
        agent_identity=agent_identity,
        committed_root=asset.committed_root,
        price=price,
        currency=currency,
        categories=tuple(asset.listing.categories or probe.package.categories),
        seller=seller_address,
        chain_id=chain_id,
        listing_contract=listing_contract,
        valuation_reference=str(valuation.to_dict()["amount"]),
        preview=asset.preview.to_dict(),
    )
    vault.write(stored, envelope=asset.envelope, content_key=asset.content_key)
    return stored, asset
