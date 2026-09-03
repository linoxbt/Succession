"""The Succession Memory Package (SMP) — a portable, model-agnostic bundle.

Nine directories, exactly as the spec fixes them:

    succession-memory-package/
    ├── identity/           agent identity, ERC-8004 reference, package version
    ├── relationships/      per-counterparty entities
    ├── preferences/        learned preferences and settings
    ├── history/            the time-ordered journal of what happened
    ├── commitments/        open promises, quotes given, terms agreed
    ├── learned-behaviors/  patterns and heuristics the agent has adapted
    ├── provenance/         origin, version, prior-owner chain, signature
    ├── permissions/        redaction flags, consent basis, access tiers
    └── integrity-proof/    Merkle root + per-category subroots

Six of those carry data; the last three are generated at build time and
describe the package rather than living inside the agent's working memory.


Two ideas make the mapping work
-------------------------------

**An SMP directory is a selection unit, not a storage location.** It is what
partial succession filters on and what gets its own Merkle subroot. It is a
disclosure boundary a seller reasons about ("sell the relationships, keep the
commitments"), which is why the standard fixes six of them rather than mirroring
whatever categories a given engine happens to use.

**Every record also carries its ``origin``** — the exact tier and category it
came from in the source engine. That is the ground truth the importer re-keys
against. So the directory grouping can be opinionated without ever being lossy:
a Sibyl entity in some category the standard never heard of lands in
``history/`` by the default map, and still comes back as *that* category in the
buyer's store, because ``origin`` says so.

The default map, and why each edge is where it is:

===================  ==========================================================
identity/            entity category ``identity``
relationships/       entity category ``relationship``; every WARM edge
                     (``entity_relations``) — an edge between two counterparties
                     is a relationship in the only sense that matters here
preferences/         entity category ``preference``
history/             the COLD journal; ARCHIVE-tier entities (Sibyl's own
                     semantics for archive are "frozen, out of the working set,
                     retrievable" — that is history); and any entity category
                     the map does not name
commitments/         entity category ``commitment``; HOT state documents — live
                     working state *is* the in-flight open work, and it is what
                     makes the cutover demo's "continues exactly where the
                     seller's agent left off" beat true rather than staged
learned-behaviors/   entity category ``learned-behavior``; REFERENCE documents
                     (the SDK's own learning pass writes accepted skills to
                     ``reference/skill/<slug>``, so reference docs are literally
                     this agent's encoded behaviors)
===================  ==========================================================


What a leaf commits to
----------------------

A leaf hashes only the fields the import contract guarantees to reproduce
byte-for-byte. Engine-assigned row ids and the ``created_at``/``updated_at``
stamps a destination store writes fresh are deliberately excluded: hashing them
would mean an honest, correct import always fails verification, which turns the
integrity check into noise. Journal ``ts`` *is* hashed, because ``write_event``
takes an explicit ``ts`` and preserves it.

Ordering ties break on the leaf's own content hash rather than on a row id, for
the same reason: two events written in the same millisecond must sort the same
way on both sides of a transfer, and their ids do not survive it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from eth_utils import keccak

from .canonical import canonical_bytes, canonical_json
from .merkle import MerkleTree, build_tree, to_hex
from .redaction import strip_reserved

__all__ = [
    "SMP_VERSION",
    "DATA_CATEGORIES",
    "GENERATED_CATEGORIES",
    "SMP_CATEGORIES",
    "DEFAULT_CATEGORY_MAP",
    "SMPPackage",
    "leaf_payload",
    "route",
    "record_sort_key",
    "build_leaves",
]

SMP_VERSION = "1.0"

#: The six directories that carry memory. These are the selectable units for
#: partial succession, and each gets its own Merkle subroot.
DATA_CATEGORIES = (
    "identity",
    "relationships",
    "preferences",
    "history",
    "commitments",
    "learned-behaviors",
)

#: Generated at build time; describe the package rather than the memory.
GENERATED_CATEGORIES = ("provenance", "permissions", "integrity-proof")

SMP_CATEGORIES = DATA_CATEGORIES + GENERATED_CATEGORIES

#: Where each source tier / entity category lands. ``None`` is the catch-all.
DEFAULT_CATEGORY_MAP: dict[str, str] = {
    # WARM entities, by their engine-side category
    "entity:identity": "identity",
    "entity:relationship": "relationships",
    "entity:preference": "preferences",
    "entity:commitment": "commitments",
    "entity:learned-behavior": "learned-behaviors",
    # Verifiable ACP job history is settled fact about what this agent did, so
    # it belongs with the journal. Named explicitly rather than left to the
    # catch-all: it is load-bearing for the valuation, and a silent change to
    # the fallback must not be able to move it.
    "entity:acp-job": "history",
    # whole tiers
    "relation": "relationships",
    "event": "history",
    "archived": "history",
    "state": "commitments",
    "reference": "learned-behaviors",
}

#: Where an entity whose category the map does not name ends up.
UNMAPPED_ENTITY_CATEGORY = "history"


def route(record: dict[str, Any], category_map: dict[str, str] | None = None) -> str:
    """Return the SMP directory a source record belongs to."""
    cmap = DEFAULT_CATEGORY_MAP if category_map is None else category_map
    kind = record["kind"]
    if kind == "entity":
        return cmap.get(f"entity:{record['category']}", UNMAPPED_ENTITY_CATEGORY)
    target = cmap.get(kind)
    if target is None:
        raise ValueError(f"no SMP route for record kind {kind!r}")
    return target


def origin_of(record: dict[str, Any]) -> dict[str, Any]:
    """The source-engine placement, preserved so the import can re-key exactly."""
    kind = record["kind"]
    if kind in ("entity", "archived"):
        return {"tier": kind, "category": record["category"], "name": record["name"]}
    if kind in ("state", "reference"):
        return {"tier": kind, "key": record["key"]}
    if kind == "relation":
        return {
            "tier": "relation",
            "from": list(record["from_key"]),
            "to": list(record["to_key"]),
            "relation_type": record["relation_type"],
        }
    if kind == "event":
        return {"tier": "event", "ts": record["ts"]}
    raise ValueError(f"unknown record kind {kind!r}")


def leaf_payload(record: dict[str, Any]) -> dict[str, Any]:
    """The exact structure that gets canonicalized and hashed for one record.

    Excludes engine row ids and destination-assigned timestamps; see the module
    docstring for why.
    """
    kind = record["kind"]
    origin = origin_of(record)
    if kind == "entity":
        return {
            "kind": "entity",
            "origin": origin,
            "status": record.get("status"),
            "body": strip_reserved(record["body"]),
        }
    if kind == "archived":
        return {
            "kind": "archived",
            "origin": origin,
            "archive_reason": record.get("archive_reason"),
            "body": strip_reserved(record["body"]),
        }
    if kind == "event":
        return {
            "kind": "event",
            "origin": origin,
            "evaluated": record.get("evaluated"),
            "acted": record.get("acted"),
            "forward": record.get("forward"),
            "extra": strip_reserved(record.get("extra")),
        }
    if kind == "state":
        return {"kind": "state", "origin": origin, "body": strip_reserved(record["body"])}
    if kind == "reference":
        return {
            "kind": "reference",
            "origin": origin,
            "body": record["body"],
            "metadata": record.get("metadata"),
        }
    if kind == "relation":
        return {"kind": "relation", "origin": origin, "metadata": record.get("metadata")}
    raise ValueError(f"unknown record kind {kind!r}")


def _primary_key(payload: dict[str, Any]) -> tuple[str, ...]:
    """Sort key fields for one leaf payload, read off its ``origin``."""
    kind = payload["kind"]
    origin = payload["origin"]
    if kind in ("entity", "archived"):
        return (origin["category"], origin["name"])
    if kind in ("state", "reference"):
        return (origin["key"],)
    if kind == "event":
        return (origin["ts"],)
    if kind == "relation":
        return (
            origin["from"][0],
            origin["from"][1],
            origin["to"][0],
            origin["to"][1],
            origin["relation_type"],
        )
    raise ValueError(f"unknown record kind {kind!r}")


def record_sort_key(payload: dict[str, Any]) -> tuple[Any, ...]:
    """Canonical order within an SMP directory.

    ``(kind, primary key, content hash)``. Grouping by kind keeps the journal
    contiguous and time-ordered inside ``history/`` even though archived
    entities share the directory. The content hash breaks ties without
    depending on a row id that the transfer does not preserve.
    """
    return (
        payload["kind"],
        _primary_key(payload),
        keccak(canonical_bytes(payload)).hex(),
    )


def build_leaves(
    data: dict[str, list[dict[str, Any]]],
) -> dict[str, list[bytes]]:
    """Canonical leaf bytes per SMP data category, in canonical order."""
    return {
        category: [canonical_bytes(p) for p in payloads]
        for category, payloads in data.items()
    }


@dataclass
class SMPPackage:
    """An in-memory SMP package: the data, plus the three generated documents."""

    data: dict[str, list[dict[str, Any]]]
    """SMP directory name -> that directory's leaf payloads, in canonical order."""

    header: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, Any] = field(default_factory=dict)

    # -- construction --------------------------------------------------

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, Any]],
        *,
        category_map: dict[str, str] | None = None,
        categories: Sequence[str] | None = None,
    ) -> "SMPPackage":
        """Route, filter, and canonically order source records.

        ``categories`` restricts the package to a subset of
        :data:`DATA_CATEGORIES` — this is partial succession, and it is the same
        pipeline as a full one with a filter applied before serialization.
        Every selected directory is present even when empty, so that a category
        deliberately sold empty is distinguishable from one that was never
        offered.
        """
        selected = tuple(categories) if categories is not None else DATA_CATEGORIES
        unknown = set(selected) - set(DATA_CATEGORIES)
        if unknown:
            raise ValueError(f"not SMP data categories: {sorted(unknown)}")

        buckets: dict[str, list[dict[str, Any]]] = {c: [] for c in selected}
        for record in records:
            target = route(record, category_map)
            if target in buckets:
                # The package carries leaf payloads, not raw source rows: what
                # ships is exactly what was hashed, with the seller's reserved
                # disclosure flags and the source engine's row ids already gone.
                buckets[target].append(leaf_payload(record))
        for category in buckets:
            buckets[category].sort(key=record_sort_key)
        return cls(data=buckets)

    # -- integrity -----------------------------------------------------

    def tree(self) -> MerkleTree:
        return build_tree(build_leaves(self.data))

    def record_count(self) -> int:
        return sum(len(v) for v in self.data.values())

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted(self.data))

    # -- serialization -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {c: self.data[c] for c in sorted(self.data)}
        out["provenance"] = self.header
        out["permissions"] = self.permissions
        out["integrity-proof"] = self.integrity
        return out

    def write_dir(self, path: str | Path) -> Path:
        """Write the nine-directory layout to disk."""
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        for category in DATA_CATEGORIES:
            d = root / category
            d.mkdir(exist_ok=True)
            records = self.data.get(category)
            # A category that was not selected writes an explicit marker rather
            # than an empty list, so a buyer can tell "sold, and empty" apart
            # from "not part of this transfer".
            payload: dict[str, Any] = (
                {"included": False, "records": []}
                if records is None
                else {"included": True, "records": records}
            )
            (d / "records.json").write_text(
                canonical_json(payload) + "\n", encoding="utf-8"
            )
        (root / "provenance").mkdir(exist_ok=True)
        (root / "provenance" / "header.json").write_text(
            canonical_json(self.header) + "\n", encoding="utf-8"
        )
        (root / "permissions").mkdir(exist_ok=True)
        (root / "permissions" / "disclosure.json").write_text(
            canonical_json(self.permissions) + "\n", encoding="utf-8"
        )
        (root / "integrity-proof").mkdir(exist_ok=True)
        (root / "integrity-proof" / "manifest.json").write_text(
            canonical_json(self.integrity) + "\n", encoding="utf-8"
        )
        return root

    @classmethod
    def read_dir(cls, path: str | Path) -> "SMPPackage":
        root = Path(path)
        missing = [c for c in SMP_CATEGORIES if not (root / c).is_dir()]
        if missing:
            raise ValueError(f"not an SMP package — missing directories: {missing}")
        data: dict[str, list[dict[str, Any]]] = {}
        for category in DATA_CATEGORIES:
            blob = json.loads((root / category / "records.json").read_text("utf-8"))
            if blob.get("included"):
                data[category] = blob["records"]
        return cls(
            data=data,
            header=json.loads((root / "provenance" / "header.json").read_text("utf-8")),
            permissions=json.loads(
                (root / "permissions" / "disclosure.json").read_text("utf-8")
            ),
            integrity=json.loads(
                (root / "integrity-proof" / "manifest.json").read_text("utf-8")
            ),
        )
