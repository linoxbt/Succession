"""Sensitivity flags, transferability, and the filter that runs before hashing.

Two independent axes, deliberately not collapsed into one enum:

``sensitivity`` — who may *see* this, and when.
    ``public``                 visible in the pre-purchase data room.
    ``private``                transfers with the sale; never in a preview.
    ``redacted-preview-only``  contributes to preview aggregates but its body
                               never leaves the seller's side before purchase.

``transferable`` — whether this may leave the seller's tenant *at all*.
    A ``False`` here is absolute. It outranks every tier, every buyer, and
    every category selection, permanently.

The ordering matters more than it looks. The spec is explicit that filtering
happens "before hashing begins, not just before display" — so a non-transferable
entity never reaches the Merkle tree in recoverable form, rather than reaching
it and being hidden by the UI. A hash commitment computed over data the buyer
must never receive is a leak waiting for someone to diff two packages.

Flags live under a reserved ``_succession`` key inside the entity body, because
Sibyl entity bodies are free-form JSON and there is no separate metadata column
to hang them on. The key is stripped from the exported payload: it describes the
seller's disclosure decision, not the agent's memory, and carrying it across
would let a buyer's own future export inherit the seller's redaction posture by
accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

__all__ = [
    "RESERVED_KEY",
    "Sensitivity",
    "Disclosure",
    "read_disclosure",
    "strip_reserved",
    "mark",
    "filter_transferable",
    "RedactionReport",
]

RESERVED_KEY = "_succession"


class Sensitivity:
    PUBLIC = "public"
    PRIVATE = "private"
    REDACTED_PREVIEW_ONLY = "redacted-preview-only"

    ALL = (PUBLIC, PRIVATE, REDACTED_PREVIEW_ONLY)


@dataclass(frozen=True)
class Disclosure:
    """One record's disclosure posture."""

    sensitivity: str = Sensitivity.PRIVATE
    transferable: bool = True

    @property
    def preview_visible(self) -> bool:
        """May this record's *content* appear before purchase? Only if public."""
        return self.sensitivity == Sensitivity.PUBLIC

    @property
    def preview_countable(self) -> bool:
        """May this record be counted in a pre-purchase aggregate?

        Everything transferable is countable — a count is the aggregate signal
        the data room exists to provide. A non-transferable record is not,
        because it is not part of what is being sold and counting it would
        overstate the asset.
        """
        return self.transferable


def read_disclosure(body: Any) -> Disclosure:
    """Read the disclosure posture off a record body.

    An unflagged record defaults to ``private`` and ``transferable``: it is part
    of the asset, but it does not leak into a preview just because nobody
    remembered to flag it. Defaulting the other way would make the safe outcome
    depend on the seller's diligence.
    """
    if not isinstance(body, dict):
        return Disclosure()
    meta = body.get(RESERVED_KEY)
    if not isinstance(meta, dict):
        return Disclosure()

    sensitivity = meta.get("sensitivity", Sensitivity.PRIVATE)
    if sensitivity not in Sensitivity.ALL:
        raise ValueError(
            f"unknown sensitivity {sensitivity!r}; expected one of {Sensitivity.ALL}"
        )
    transferable = meta.get("transferable", True)
    if not isinstance(transferable, bool):
        raise ValueError(
            f"'transferable' must be a bool, got {type(transferable).__name__}"
        )
    return Disclosure(sensitivity=sensitivity, transferable=transferable)


def strip_reserved(body: Any) -> Any:
    """Return ``body`` without the reserved disclosure key."""
    if not isinstance(body, dict) or RESERVED_KEY not in body:
        return body
    return {k: v for k, v in body.items() if k != RESERVED_KEY}


def mark(
    body: dict[str, Any],
    *,
    sensitivity: str | None = None,
    transferable: bool | None = None,
) -> dict[str, Any]:
    """Return a copy of ``body`` with disclosure flags set. Seller-side helper."""
    if sensitivity is not None and sensitivity not in Sensitivity.ALL:
        raise ValueError(f"unknown sensitivity {sensitivity!r}")
    meta = dict(body.get(RESERVED_KEY) or {}) if isinstance(body, dict) else {}
    if sensitivity is not None:
        meta["sensitivity"] = sensitivity
    if transferable is not None:
        meta["transferable"] = transferable
    return {**body, RESERVED_KEY: meta}


@dataclass(frozen=True)
class RedactionReport:
    """What the filter removed. Ships in the package's ``permissions/`` directory.

    Counts only — naming a withheld entity would defeat the point of
    withholding it.
    """

    withheld_non_transferable: int = 0
    withheld_by_category_filter: int = 0
    withheld_dangling_relations: int = 0
    categories_selected: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "withheld_non_transferable": self.withheld_non_transferable,
            "withheld_by_category_filter": self.withheld_by_category_filter,
            "withheld_dangling_relations": self.withheld_dangling_relations,
            "categories_selected": list(self.categories_selected),
        }


def filter_transferable(
    records: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Drop non-transferable records. Returns ``(kept, withheld_count)``.

    This is the gate that runs before serialization, and therefore before
    hashing.
    """
    kept: list[dict[str, Any]] = []
    withheld = 0
    for record in records:
        if read_disclosure(record.get("body")).transferable:
            kept.append(record)
        else:
            withheld += 1
    return kept, withheld
