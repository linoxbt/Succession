"""Build, hash, and sign an SMP package from a live tenant.

Order of operations is the load-bearing part, and it is the order the spec
insists on: **filter, then serialize, then hash.** A non-transferable entity is
gone before the Merkle tree is built, so it never reaches the commitment in
recoverable form. Filtering at display time instead would leave the withheld
content inside the hashed structure, where anyone who could diff two packages
could recover it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .canonical import canonical_bytes
from .memory.base import MemorySource
from .merkle import to_hex
from .provenance import build_header, sign_header
from .redaction import Consent, RedactionReport, filter_transferable, read_disclosure
from .smp import DATA_CATEGORIES, SMPPackage, route

__all__ = ["ExportResult", "read_all", "build_package", "export_tenant", "memory_version_of"]


def read_all(source: MemorySource) -> list[dict[str, Any]]:
    """Every record in every tier. This is the asset, before any filtering."""
    return [
        *source.entities(),
        *source.relations(),
        *source.events(),
        *source.states(),
        *source.references(),
        *source.archived(),
    ]


def memory_version_of(source: MemorySource) -> int:
    """The tenant's memory version.

    The spec offers two readings and calls the second the cheapest correct one:
    a counter the export tool bumps, or the count of COLD journal entries at
    export time. The journal count is used here because it needs no extra state
    and cannot drift from reality — every meaningful action an agent takes
    writes a journal event, so the count *is* a monotonic version of the
    tenant's history. A stored counter would be one more thing that can be
    wrong, and a buyer has no way to audit it.
    """
    return len(source.events())


@dataclass
class ExportResult:
    package: SMPPackage
    root: bytes
    record_count: int
    redaction: RedactionReport

    @property
    def root_hex(self) -> str:
        return to_hex(self.root)


def build_package(
    source: MemorySource,
    *,
    categories: Sequence[str] | None = None,
    category_map: dict[str, str] | None = None,
) -> tuple[SMPPackage, RedactionReport]:
    """Filter and route a tenant's records into an unsigned SMP package."""
    records = read_all(source)
    kept, withheld_non_transferable, withheld_without_consent = filter_transferable(
        records
    )

    selected = tuple(categories) if categories is not None else DATA_CATEGORIES
    withheld_by_category = sum(
        1 for r in kept if route(r, category_map) not in set(selected)
    )

    kept, withheld_dangling = _prune_dangling_relations(
        kept, selected=set(selected), category_map=category_map
    )

    package = SMPPackage.from_records(
        kept, category_map=category_map, categories=selected
    )
    report = RedactionReport(
        withheld_non_transferable=withheld_non_transferable,
        withheld_without_consent=withheld_without_consent,
        withheld_by_category_filter=withheld_by_category,
        withheld_dangling_relations=withheld_dangling,
        categories_selected=tuple(sorted(selected)),
    )
    return package, report


def _prune_dangling_relations(
    records: list[dict[str, Any]],
    *,
    selected: set[str],
    category_map: dict[str, str] | None,
) -> tuple[list[dict[str, Any]], int]:
    """Drop edges whose endpoints are not both in the package — before hashing.

    An edge survives redaction and category filtering more easily than the
    entities it connects: it lives in ``relationships/`` regardless of where its
    endpoints landed. So a package can end up committing to an edge pointing at
    an entity the buyer will never receive — because the endpoint was marked
    non-transferable, or because its category was not part of a partial sale.

    Left alone, that is not merely untidy, it breaks verification: the importer
    cannot re-link an edge to an entity that does not exist, so it drops the
    edge, and the re-hash of the destination store then disagrees with the
    committed root on an otherwise perfectly honest transfer. Pruning here — on
    the same side of the line as every other filter, before serialization —
    keeps the commitment and the deliverable describing the same thing.

    One consequence, worth stating rather than discovering later: because the
    edges all live in ``relationships/``, that category's content — and so its
    Merkle subroot — depends on which *other* categories travel with it. Every
    other category's subroot is a function of its own content alone. So a
    partial sale commits its own root over exactly what is being sold, and the
    "verify a subroot against the full listing's root" shortcut holds for the
    categories that carry no cross-category edges, but not for
    ``relationships``.
    """
    present: set[tuple[str, str]] = {
        (r["category"], r["name"])
        for r in records
        if r["kind"] == "entity" and route(r, category_map) in selected
    }
    kept: list[dict[str, Any]] = []
    dropped = 0
    for record in records:
        if record["kind"] == "relation" and route(record, category_map) in selected:
            endpoints = (tuple(record["from_key"]), tuple(record["to_key"]))
            if not all(e in present for e in endpoints):
                dropped += 1
                continue
        kept.append(record)
    return kept, dropped


def export_tenant(
    source: MemorySource,
    *,
    agent_identity: str,
    private_key: str,
    categories: Sequence[str] | None = None,
    category_map: dict[str, str] | None = None,
    provenance_chain: list[dict[str, Any]] | None = None,
    created_at: str | None = None,
) -> ExportResult:
    """The full export: filter → serialize → hash → sign.

    ``private_key`` must be the key behind the wallet that holds the agent's
    ERC-8004 identity. That is what makes the signature mean "the agent being
    sold attested to this", rather than "some key attested to this".
    """
    package, report = build_package(
        source, categories=categories, category_map=category_map
    )
    tree = package.tree()

    permissions = {
        "policy_version": "1.0",
        "tiers": {
            "preview": "aggregate statistics only; no record bodies",
            "full": "every record in the package, post-purchase and hash-verified",
        },
        "redaction": report.to_dict(),
        # Previously a single sentence asserting the seller had authority over
        # every record alike. That applied equally to a book the seller had a
        # defensible basis for and to one they did not, so it told a buyer
        # nothing. This reports what the filter actually did instead.
        "consent": {
            "policy": (
                "Each record carries its own basis. Records marked 'withheld' "
                "are filtered before hashing and are not in the package or the "
                "Merkle tree."
            ),
            "bases": list(Consent.TRANSFERABLE),
            "withheld_without_consent": report.withheld_without_consent,
            "operator_responsibility": (
                "The basis recorded against each record is the operator's "
                "judgement against their own terms with their counterparties. "
                "This package enforces the flag; it does not adjudicate it."
            ),
        },
    }

    header = build_header(
        agent_identity=agent_identity,
        integrity_root=to_hex(tree.root),
        memory_version=memory_version_of(source),
        categories=list(package.categories),
        permissions=permissions,
        provenance_chain=provenance_chain,
        created_at=created_at,
    )
    package.header = sign_header(header, private_key)
    package.permissions = permissions
    package.integrity = tree.to_manifest()

    return ExportResult(
        package=package,
        root=tree.root,
        record_count=package.record_count(),
        redaction=report,
    )
