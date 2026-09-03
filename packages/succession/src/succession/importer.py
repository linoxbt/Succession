"""Import an SMP package into a fresh tenant, then prove it arrived intact.

The verification that matters is not "did the bytes we received hash to the
committed root" — that only proves the courier was honest. It is **re-hash the
destination store after the write**, which additionally proves the importer
wrote what it received, that the destination engine did not silently coerce
anything, and that nothing was lost to a constraint violation on the way in.
That is the check :func:`import_package` performs, and it is why the round trip
runs the whole export pipeline a second time against the buyer's own tenant.

Re-keying is the other half. Records carry their ``origin`` — the tier and
category they held in the seller's store — and are written back through the
destination's own public API under the buyer's ``tenant_id``. The
``(tenant_id, category, name)`` uniqueness constraint that makes the asset clean
in the first place is what the fresh-tenant requirement protects: writing into a
tenant that already holds records would silently update rows on collision, and a
silent update is data loss wearing a success message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonical import canonical_bytes
from .export import build_package
from .memory.base import (
    archived_record,
    entity_record,
    event_record,
    reference_record,
    relation_record,
    state_record,
)
from .merkle import from_hex, to_hex
from .provenance import SignatureError, verify_header
from .smp import SMPPackage

__all__ = [
    "ImportError_",
    "IntegrityMismatch",
    "ImportResult",
    "rehydrate",
    "import_package",
    "verify_package",
]


class ImportError_(Exception):
    """The package cannot be imported."""


class IntegrityMismatch(ImportError_):
    """Delivered content does not match the commitment. Triggers the refund path."""

    def __init__(self, message: str, *, committed: str, delivered: str) -> None:
        super().__init__(message)
        self.committed = committed
        self.delivered = delivered


@dataclass
class ImportResult:
    tenant_id: str
    records_written: dict[str, int] = field(default_factory=dict)
    committed_root: str = ""
    delivered_root: str = ""
    reimported_root: str = ""
    signer: str = ""

    @property
    def total_records(self) -> int:
        return sum(self.records_written.values())

    @property
    def verified(self) -> bool:
        return (
            bool(self.committed_root)
            and self.committed_root == self.delivered_root == self.reimported_root
        )


def verify_package(
    package: SMPPackage,
    *,
    committed_root: str,
    expected_signer: str,
) -> str:
    """Check a received package against the listing-time commitment.

    Runs before a single row is written. Returns the recovered signer address.
    """
    delivered_root = to_hex(package.tree().root)

    header_root = package.header.get("integrity_root")
    if header_root != delivered_root:
        raise IntegrityMismatch(
            "package contents do not match the root in their own provenance header",
            committed=header_root or "",
            delivered=delivered_root,
        )

    if from_hex(committed_root) != from_hex(delivered_root):
        raise IntegrityMismatch(
            "delivered memory does not match the committed hash",
            committed=committed_root,
            delivered=delivered_root,
        )

    manifest_root = (package.integrity or {}).get("root")
    if manifest_root != delivered_root:
        raise IntegrityMismatch(
            "integrity-proof manifest does not match the package it describes",
            committed=manifest_root or "",
            delivered=delivered_root,
        )

    # The signature covers the whole header, so this also authenticates
    # agent_identity, the category list, and the provenance chain.
    return verify_header(package.header, expected_signer)


def rehydrate(package: SMPPackage) -> dict[str, list[dict[str, Any]]]:
    """Turn package records back into per-tier writes, keyed by ``origin``."""
    out: dict[str, list[dict[str, Any]]] = {
        "entity": [],
        "relation": [],
        "event": [],
        "state": [],
        "reference": [],
        "archived": [],
    }
    for records in package.data.values():
        for rec in records:
            kind = rec["kind"]
            if kind not in out:
                raise ImportError_(f"unknown record kind in package: {kind!r}")
            out[kind].append(rec)
    return out


def import_package(
    package: SMPPackage,
    sink: Any,
    *,
    committed_root: str,
    expected_signer: str,
    category_map: dict[str, str] | None = None,
) -> ImportResult:
    """Verify, write into a fresh tenant, then re-hash the destination.

    Raises :class:`IntegrityMismatch` on any mismatch — before writing if the
    delivered package is wrong, after writing if the destination store did not
    faithfully reproduce it. Either way the caller's refund path is the same.
    """
    signer = verify_package(
        package, committed_root=committed_root, expected_signer=expected_signer
    )

    if not sink.is_empty():
        raise ImportError_(
            f"tenant {sink.tenant_id!r} already holds records; an SMP package "
            "imports only into a fresh tenant (merging two evolved memories is "
            "the 'merge' primitive, and it is not this pipeline)"
        )

    by_kind = rehydrate(package)
    written: dict[str, int] = {}

    written["entity"] = sink.write_entities(
        entity_record(
            category=r["origin"]["category"],
            name=r["origin"]["name"],
            body=r["body"],
            status=r.get("status"),
        )
        for r in by_kind["entity"]
    )
    written["event"] = sink.write_events(
        event_record(
            id="",
            ts=r["origin"]["ts"],
            evaluated=r.get("evaluated"),
            acted=r.get("acted"),
            forward=r.get("forward"),
            extra=r.get("extra"),
        )
        for r in by_kind["event"]
    )
    written["state"] = sink.write_states(
        state_record(key=r["origin"]["key"], body=r["body"]) for r in by_kind["state"]
    )
    written["reference"] = sink.write_references(
        reference_record(
            key=r["origin"]["key"], body=r["body"], metadata=r.get("metadata")
        )
        for r in by_kind["reference"]
    )
    written["archived"] = sink.write_archived(
        archived_record(
            category=r["origin"]["category"],
            name=r["origin"]["name"],
            body=r["body"],
            archive_reason=r.get("archive_reason"),
        )
        for r in by_kind["archived"]
    )
    # Edges last: both endpoints must already exist to be re-linked by key.
    written["relation"] = sink.write_relations(
        relation_record(
            from_key=tuple(r["origin"]["from"]),
            to_key=tuple(r["origin"]["to"]),
            relation_type=r["origin"]["relation_type"],
            metadata=r.get("metadata"),
        )
        for r in by_kind["relation"]
    )

    # The real check: re-export the destination and re-derive the root from
    # what is actually in the buyer's store now.
    reimported, _ = build_package(
        sink,
        categories=list(package.data.keys()),
        category_map=category_map,
    )
    reimported_root = to_hex(reimported.tree().root)

    result = ImportResult(
        tenant_id=sink.tenant_id,
        records_written=written,
        committed_root=committed_root,
        delivered_root=to_hex(package.tree().root),
        reimported_root=reimported_root,
        signer=signer,
    )

    if from_hex(reimported_root) != from_hex(committed_root):
        raise IntegrityMismatch(
            "re-imported memory does not reproduce the committed hash",
            committed=committed_root,
            delivered=reimported_root,
        )
    return result
