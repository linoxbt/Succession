"""The marketplace's metadata store — and nothing more than that.

What is authoritative lives on chain: who is selling, what they committed to,
the price, the state, the escrow. This module holds only what the contract has
no field for and no business holding — the data-room counts, the reference
valuation, the agent's display name — and every row is supplied by the seller
who owns the listing.

That split is the point. A marketplace that stored its own idea of a listing's
price or state would eventually disagree with the chain, and the chain would be
right. So the read path joins: the contract for truth, this table for the parts
that are presentational.

Rows are accepted only from the address the contract records as that listing's
seller, proven by a signature over the listing id. There is no account, no
password and no session — the seller already holds the key the contract knows
about, so nothing else needs to be invented.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

__all__ = ["MetadataRegistry", "ListingMetadata"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS listing_metadata (
  listing_id      TEXT PRIMARY KEY,
  seller          TEXT NOT NULL,
  agent_identity  TEXT NOT NULL,
  committed_root  TEXT NOT NULL,
  chain_id        INTEGER NOT NULL,
  contract        TEXT NOT NULL,
  name            TEXT NOT NULL DEFAULT '',
  vertical        TEXT NOT NULL DEFAULT '',
  valuation       TEXT NOT NULL DEFAULT '',
  preview         TEXT NOT NULL DEFAULT '{}',
  envelope        TEXT NOT NULL DEFAULT '',
  posted_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS listing_metadata_seller ON listing_metadata (seller);
"""


class ListingMetadata(dict):
    """A metadata row. A dict because it is passed straight through to JSON."""


class MetadataRegistry:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def put(
        self,
        *,
        listing_id: str,
        seller: str,
        agent_identity: str,
        committed_root: str,
        chain_id: int,
        contract: str,
        name: str = "",
        vertical: str = "",
        valuation: str = "",
        preview: dict[str, Any] | None = None,
        envelope: dict[str, Any] | None = None,
        posted_at: str,
    ) -> None:
        """Upsert one listing's metadata.

        The envelope is stored as supplied: it is AES-256-GCM ciphertext and is
        useless without the content key, which the seller keeps and releases
        only when they have seen escrow funded on chain themselves. Holding it
        here means a buyer can fetch it the moment they pay rather than waiting
        on the seller's connection for the bytes as well as the key.
        """
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO listing_metadata (listing_id, seller, agent_identity, "
                "committed_root, chain_id, contract, name, vertical, valuation, "
                "preview, envelope, posted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(listing_id) DO UPDATE SET "
                "name=excluded.name, vertical=excluded.vertical, "
                "valuation=excluded.valuation, preview=excluded.preview, "
                "envelope=excluded.envelope, posted_at=excluded.posted_at",
                (
                    listing_id,
                    seller,
                    agent_identity,
                    committed_root,
                    int(chain_id),
                    contract,
                    name,
                    vertical,
                    valuation,
                    json.dumps(preview or {}),
                    json.dumps(envelope) if envelope else "",
                    posted_at,
                ),
            )

    def get(self, listing_id: str) -> ListingMetadata | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM listing_metadata WHERE listing_id = ?", (listing_id,)
            ).fetchone()
        return self._row(row) if row else None

    def all(self) -> list[ListingMetadata]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM listing_metadata ORDER BY posted_at DESC"
            ).fetchall()
        return [self._row(r) for r in rows]

    def envelope(self, listing_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT envelope FROM listing_metadata WHERE listing_id = ?",
                (listing_id,),
            ).fetchone()
        if row is None or not row["envelope"]:
            return None
        return json.loads(row["envelope"])

    def delete(self, listing_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM listing_metadata WHERE listing_id = ?", (listing_id,)
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> ListingMetadata:
        return ListingMetadata(
            listing_id=row["listing_id"],
            seller=row["seller"],
            agent_identity=row["agent_identity"],
            committed_root=row["committed_root"],
            chain_id=row["chain_id"],
            contract=row["contract"],
            name=row["name"],
            vertical=row["vertical"],
            valuation=row["valuation"],
            preview=json.loads(row["preview"] or "{}"),
            posted_at=row["posted_at"],
            # The ciphertext is deliberately not in the listing view: it is
            # bulk, and it has its own route.
            has_envelope=bool(row["envelope"]),
        )
