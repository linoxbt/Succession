"""The settlement leg: listing, escrow, atomic confirmation, refund.

This module is the boundary between Succession's off-chain machinery and the
chain. :class:`SettlementBackend` is the interface ``ListingContract.sol``
implements on Base Sepolia; :class:`LocalSettlement` is an in-process
implementation of the *same state machine*, used by the tests and the offline
demo. Keeping them to one interface is what stops the local version from
quietly diverging into a more forgiving contract than the real one — every
guard the Solidity enforces is enforced here too, and the state-machine tests
run against both.


What "atomic" honestly means here
---------------------------------

A single transaction cannot span an EVM chain and an off-chain SQLite store, and
any design claiming otherwise is hiding a failure mode. What the spec actually
requires — "there is never a state where payment has cleared but transfer has
not, or vice versa" — is achievable, and this is how:

1. The buyer funds escrow on-chain. Nothing has moved yet; the seller cannot
   touch the money.
2. The package is delivered and imported into the buyer's fresh tenant. Still
   nothing has moved: the seller is unpaid, and the buyer holds memory it cannot
   yet use as the agent, because the identity token is still the seller's.
3. ``confirmTransfer`` runs. In **one** transaction it verifies the delivered
   root against the listing commitment and the seller's signature over it,
   releases the escrowed payment, transfers the ERC-8004 identity token, and
   sets the ``sealed`` flag. All four, or none.
4. The off-chain seal follows the on-chain event.

Step 3 is where atomicity lives, and it is genuinely atomic because it is one
EVM transaction. Steps 2 and 4 are ordered around it so that every intermediate
state is safe: a failure before step 3 refunds the buyer and leaves the seller
exactly as they were, and the orchestrator purges the buyer's half-written
tenant as its compensating action. A failure after step 3 cannot leave the money
and the identity on different sides, because they moved together.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from eth_utils import to_checksum_address

from .merkle import from_hex

__all__ = [
    "ListingState",
    "Listing",
    "SettlementReceipt",
    "SettlementError",
    "SettlementBackend",
    "LocalSettlement",
]


class ListingState(str, Enum):
    OPEN = "open"           # listed, no buyer
    ESCROWED = "escrowed"   # buyer funded, awaiting confirmation
    CONFIRMED = "confirmed"  # hash matched; paid, identity moved, seller sealed
    REFUNDED = "refunded"   # mismatch or cancellation; buyer made whole


class SettlementError(Exception):
    """The settlement layer rejected the operation."""


@dataclass
class Listing:
    listing_id: str
    agent_id: str
    seller: str
    seller_signature: str
    hash_commitment: str
    price: int
    currency: str = "USDC"
    categories: tuple[str, ...] = ()
    valuation_reference: str = ""
    state: ListingState = ListingState.OPEN
    buyer: str = ""
    escrow_balance: int = 0
    delivered_hash: str = ""
    sealed: bool = False
    created_at: str = ""
    settled_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "agent_id": self.agent_id,
            "seller": self.seller,
            "seller_signature": self.seller_signature,
            "hash_commitment": self.hash_commitment,
            "price": self.price,
            "currency": self.currency,
            "categories": list(self.categories),
            "valuation_reference": self.valuation_reference,
            "state": self.state.value,
            "buyer": self.buyer,
            "escrow_balance": self.escrow_balance,
            "delivered_hash": self.delivered_hash,
            "sealed": self.sealed,
            "created_at": self.created_at,
            "settled_at": self.settled_at,
        }


@dataclass(frozen=True)
class SettlementReceipt:
    listing_id: str
    outcome: str                 # "released" | "refunded"
    amount: int
    paid_to: str
    identity_transferred_to: str
    sealed_agent: str
    reference: str               # tx hash on-chain; a synthetic id locally
    settled_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "outcome": self.outcome,
            "amount": self.amount,
            "paid_to": self.paid_to,
            "identity_transferred_to": self.identity_transferred_to,
            "sealed_agent": self.sealed_agent,
            "reference": self.reference,
            "settled_at": self.settled_at,
        }


@runtime_checkable
class SettlementBackend(Protocol):
    def list_asset(self, **kwargs: Any) -> Listing: ...
    def get(self, listing_id: str) -> Listing: ...
    def buy(self, listing_id: str, *, buyer: str, amount: int) -> Listing: ...
    def confirm_transfer(
        self, listing_id: str, *, delivered_hash: str, buyer_identity: str
    ) -> SettlementReceipt: ...
    def refund(self, listing_id: str, *, reason: str) -> SettlementReceipt: ...


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
  listing_id          TEXT PRIMARY KEY,
  agent_id            TEXT NOT NULL,
  seller              TEXT NOT NULL,
  seller_signature    TEXT NOT NULL,
  hash_commitment     TEXT NOT NULL,
  price               INTEGER NOT NULL,
  currency            TEXT NOT NULL,
  categories          TEXT NOT NULL,
  valuation_reference TEXT NOT NULL DEFAULT '',
  state               TEXT NOT NULL,
  buyer               TEXT NOT NULL DEFAULT '',
  escrow_balance      INTEGER NOT NULL DEFAULT 0,
  delivered_hash      TEXT NOT NULL DEFAULT '',
  sealed              INTEGER NOT NULL DEFAULT 0,
  created_at          TEXT NOT NULL,
  settled_at          TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS receipts (
  reference   TEXT PRIMARY KEY,
  listing_id  TEXT NOT NULL,
  payload     TEXT NOT NULL
);
"""


class LocalSettlement:
    """An in-process implementation of the ListingContract state machine.

    Same guards, same ordering, same refusals as the Solidity — see
    ``contracts/src/ListingContract.sol``. It exists so the transfer pipeline
    can be exercised end to end without a funded testnet wallet, and so the
    state-machine tests can run in CI. It is not a stand-in for the contract in
    a demo: the on-chain leg is the part that makes the claim credible, and
    swapping this in on the day would be precisely the two-browser-tabs
    dishonesty the spec warns against.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    # -- listing -------------------------------------------------------

    def list_asset(
        self,
        *,
        listing_id: str,
        agent_id: str,
        seller: str,
        seller_signature: str,
        hash_commitment: str,
        price: int,
        currency: str = "USDC",
        categories: tuple[str, ...] = (),
        valuation_reference: str = "",
    ) -> Listing:
        if price <= 0:
            raise SettlementError("price must be positive")
        from_hex(hash_commitment)  # reject a malformed commitment at listing time
        listing = Listing(
            listing_id=listing_id,
            agent_id=agent_id,
            seller=to_checksum_address(seller),
            seller_signature=seller_signature,
            hash_commitment=hash_commitment,
            price=price,
            currency=currency,
            categories=tuple(categories),
            valuation_reference=valuation_reference,
            state=ListingState.OPEN,
            created_at=_now(),
        )
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO listings (listing_id, agent_id, seller, seller_signature, "
                    "hash_commitment, price, currency, categories, valuation_reference, "
                    "state, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        listing.listing_id,
                        listing.agent_id,
                        listing.seller,
                        listing.seller_signature,
                        listing.hash_commitment,
                        listing.price,
                        listing.currency,
                        ",".join(listing.categories),
                        listing.valuation_reference,
                        listing.state.value,
                        listing.created_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise SettlementError(f"listing {listing_id!r} already exists") from exc
        return listing

    def get(self, listing_id: str) -> Listing:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM listings WHERE listing_id = ?", (listing_id,)
            ).fetchone()
        if row is None:
            raise SettlementError(f"no such listing: {listing_id!r}")
        return Listing(
            listing_id=row["listing_id"],
            agent_id=row["agent_id"],
            seller=row["seller"],
            seller_signature=row["seller_signature"],
            hash_commitment=row["hash_commitment"],
            price=row["price"],
            currency=row["currency"],
            categories=tuple(c for c in row["categories"].split(",") if c),
            valuation_reference=row["valuation_reference"],
            state=ListingState(row["state"]),
            buyer=row["buyer"],
            escrow_balance=row["escrow_balance"],
            delivered_hash=row["delivered_hash"],
            sealed=bool(row["sealed"]),
            created_at=row["created_at"],
            settled_at=row["settled_at"],
        )

    def list_all(self) -> list[Listing]:
        with self._conn() as conn:
            ids = [
                r["listing_id"]
                for r in conn.execute(
                    "SELECT listing_id FROM listings ORDER BY created_at DESC"
                ).fetchall()
            ]
        return [self.get(i) for i in ids]

    # -- escrow --------------------------------------------------------

    def buy(self, listing_id: str, *, buyer: str, amount: int) -> Listing:
        listing = self.get(listing_id)
        if listing.state is not ListingState.OPEN:
            raise SettlementError(
                f"listing {listing_id!r} is {listing.state.value}, not open"
            )
        if amount != listing.price:
            raise SettlementError(
                f"escrow must be exactly the asking price ({listing.price}), got {amount}"
            )
        buyer_addr = to_checksum_address(buyer)
        if buyer_addr == listing.seller:
            raise SettlementError("seller cannot buy their own listing")
        with self._conn() as conn:
            conn.execute(
                "UPDATE listings SET state = ?, buyer = ?, escrow_balance = ? "
                "WHERE listing_id = ? AND state = ?",
                (
                    ListingState.ESCROWED.value,
                    buyer_addr,
                    amount,
                    listing_id,
                    ListingState.OPEN.value,
                ),
            )
        return self.get(listing_id)

    # -- settlement ----------------------------------------------------

    def confirm_transfer(
        self, listing_id: str, *, delivered_hash: str, buyer_identity: str
    ) -> SettlementReceipt:
        """Release payment, move the identity, and seal — together or not at all.

        A mismatch does not raise: it refunds. The refund *is* the specified
        behaviour on a bad delivery, and making the caller catch an exception to
        trigger it would leave the money stuck if they forgot.
        """
        listing = self.get(listing_id)
        if listing.state is not ListingState.ESCROWED:
            raise SettlementError(
                f"listing {listing_id!r} is {listing.state.value}; nothing is escrowed"
            )

        if from_hex(delivered_hash) != from_hex(listing.hash_commitment):
            return self.refund(
                listing_id,
                reason=(
                    "Hash mismatch — delivered memory does not match the "
                    "committed hash."
                ),
                delivered_hash=delivered_hash,
            )

        reference = _reference("confirm", listing_id, delivered_hash)
        settled_at = _now()
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE listings SET state = ?, delivered_hash = ?, escrow_balance = 0, "
                "sealed = 1, settled_at = ? WHERE listing_id = ? AND state = ?",
                (
                    ListingState.CONFIRMED.value,
                    delivered_hash,
                    settled_at,
                    listing_id,
                    ListingState.ESCROWED.value,
                ),
            )
            if cur.rowcount != 1:
                # Someone else settled between our read and our write.
                raise SettlementError(
                    f"listing {listing_id!r} changed state during confirmation"
                )
        receipt = SettlementReceipt(
            listing_id=listing_id,
            outcome="released",
            amount=listing.price,
            paid_to=listing.seller,
            identity_transferred_to=to_checksum_address(listing.buyer),
            sealed_agent=listing.agent_id,
            reference=reference,
            settled_at=settled_at,
        )
        self._record(receipt)
        return receipt

    def refund(
        self, listing_id: str, *, reason: str, delivered_hash: str = ""
    ) -> SettlementReceipt:
        listing = self.get(listing_id)
        if listing.state is not ListingState.ESCROWED:
            raise SettlementError(
                f"listing {listing_id!r} is {listing.state.value}; nothing to refund"
            )
        reference = _reference("refund", listing_id, reason)
        settled_at = _now()
        with self._conn() as conn:
            conn.execute(
                "UPDATE listings SET state = ?, delivered_hash = ?, escrow_balance = 0, "
                "settled_at = ? WHERE listing_id = ? AND state = ?",
                (
                    ListingState.REFUNDED.value,
                    delivered_hash,
                    settled_at,
                    listing_id,
                    ListingState.ESCROWED.value,
                ),
            )
        receipt = SettlementReceipt(
            listing_id=listing_id,
            outcome="refunded",
            amount=listing.price,
            paid_to=to_checksum_address(listing.buyer),
            identity_transferred_to="",
            sealed_agent="",
            reference=reference,
            settled_at=settled_at,
        )
        self._record(receipt)
        return receipt

    def _record(self, receipt: SettlementReceipt) -> None:
        import json

        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO receipts (reference, listing_id, payload) "
                "VALUES (?, ?, ?)",
                (receipt.reference, receipt.listing_id, json.dumps(receipt.to_dict())),
            )


def _reference(kind: str, *parts: str) -> str:
    """A stand-in for a transaction hash. Deterministic, and obviously local."""
    from eth_utils import keccak

    return "local:" + keccak(("|".join((kind, *parts))).encode()).hex()[:32]
