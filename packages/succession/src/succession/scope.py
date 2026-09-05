"""What is on offer, and how much of it a seller is actually selling.

Two jobs, and they belong together because the second is meaningless without
the first.

**Inventory.** Before a seller can choose a scope they need to see what they
have. An agent that has never written a preference cannot sell preferences, and
offering the category anyway produces a listing whose `preferences/` directory
exports empty. So the inventory is read from the store itself and reports, per
category, how many records are genuinely sellable, how many the seller withheld,
how many consent blocks, and how deep the category runs.

**Selection.** A seller says "sixty percent of learned-behaviors" and that has
to resolve to an exact, reproducible set of records, because the buyer re-hashes
what lands in their store and compares it to a root committed before they
existed. A selection rule that produced a different set on a second run would
break verification outright.

So the rule is fixed and stated:

    Records in a category are ordered newest first. A percentage takes that
    many from the front, rounded up, so any non-zero percentage of a non-empty
    category yields at least one record.

Newest-first because recent context is what a successor agent needs to operate:
the open commitment, the last thing a counterparty said, the rate that was
quoted this week. Selling the oldest sixty percent of a freight agent's memory
would hand over history and withhold the part that does work.

Ties are broken on **content hash, never row id**. Row ids do not survive a
transfer, so ordering by one would make the seller's selection unreproducible on
the buyer's side, which is the same reason the Merkle leaves exclude them.

A seller who wants exact control picks records individually instead, and an
explicit pick always overrides a percentage for that category.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from eth_utils import keccak

from .canonical import canonical_bytes
from .redaction import read_disclosure
from .smp import DATA_CATEGORIES, route

__all__ = [
    "CategoryInventory",
    "CategorySelection",
    "SaleScope",
    "record_fingerprint",
    "record_timestamp",
    "take_inventory",
]


def record_timestamp(record: dict[str, Any]) -> str:
    """The record's own time, whatever kind of record it is.

    Each tier names this differently — an event has ``ts``, an entity has
    ``updated_at``, a relation only ``created_at`` — so ordering across a mixed
    category needs one accessor rather than five branches at every call site.
    Missing is an empty string, which sorts oldest, so an undated record ends up
    at the back of a newest-first list rather than the front.
    """
    for key in ("ts", "updated_at", "created_at"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def record_fingerprint(record: dict[str, Any]) -> str:
    """A stable identifier derived from content, not from storage.

    Used to break ties in the ordering and to name records when a seller picks
    them individually. Deliberately excludes the row id: ids are assigned by
    whichever store the record happens to live in and do not survive a transfer,
    so a selection keyed on them could not be reproduced by the buyer.
    """
    material = {k: v for k, v in record.items() if k != "id"}
    return "0x" + keccak(canonical_bytes(material)).hex()[:16]


def _sort_key(record: dict[str, Any]) -> tuple[str, str]:
    # Negated by reversing later; the fingerprint is the deterministic
    # tie-break for records written in the same second.
    return (record_timestamp(record), record_fingerprint(record))


@dataclass(frozen=True)
class CategoryInventory:
    """What one category actually holds."""

    category: str
    sellable: int
    withheld_by_seller: int
    withheld_without_consent: int
    newest: str = ""
    oldest: str = ""

    @property
    def total(self) -> int:
        return self.sellable + self.withheld_by_seller + self.withheld_without_consent

    @property
    def depth(self) -> str:
        """A word for how much is here.

        Bands rather than a raw count, because "31 records" means nothing
        without knowing what is normal for the category, and a seller choosing
        a scope needs to know whether a directory is worth offering at all.
        """
        if self.sellable == 0:
            return "empty"
        if self.sellable < 5:
            return "thin"
        if self.sellable < 20:
            return "moderate"
        return "deep"

    @property
    def offerable(self) -> bool:
        """Whether this category can honestly be part of a sale.

        A category with nothing sellable in it must not be selectable. Offering
        it produces a listing that exports an empty directory, which is a
        promise the package cannot keep.
        """
        return self.sellable > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "sellable": self.sellable,
            "withheld_by_seller": self.withheld_by_seller,
            "withheld_without_consent": self.withheld_without_consent,
            "total": self.total,
            "depth": self.depth,
            "offerable": self.offerable,
            "newest": self.newest,
            "oldest": self.oldest,
        }


@dataclass(frozen=True)
class CategorySelection:
    """How much of one category is being sold."""

    category: str
    #: 0-100. Ignored when ``fingerprints`` is set.
    percent: int = 100
    #: Exact records, by content fingerprint. Overrides ``percent`` entirely,
    #: because a seller who has named records means those records.
    fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.percent <= 100:
            raise ValueError(
                f"{self.category}: percent must be 0-100, got {self.percent}"
            )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"category": self.category, "percent": self.percent}
        if self.fingerprints:
            out["fingerprints"] = list(self.fingerprints)
        return out


@dataclass(frozen=True)
class SaleScope:
    """The whole offer: which categories, and how much of each.

    An empty scope means everything, so existing callers that pass no scope
    keep selling the whole memory.
    """

    selections: tuple[CategorySelection, ...] = field(default_factory=tuple)

    @classmethod
    def everything(cls) -> "SaleScope":
        return cls(tuple(CategorySelection(c, 100) for c in DATA_CATEGORIES))

    @classmethod
    def from_percentages(cls, percentages: dict[str, int]) -> "SaleScope":
        """Build a scope from ``{"learned-behaviors": 60, ...}``.

        A category absent from the mapping is not sold at all, which makes the
        mapping the complete statement of the offer rather than a set of
        adjustments to an implied default.
        """
        return cls(
            tuple(
                CategorySelection(category, percent)
                for category, percent in percentages.items()
                if percent > 0
            )
        )

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(s.category for s in self.selections if s.percent > 0 or s.fingerprints)

    def selection_for(self, category: str) -> CategorySelection | None:
        for selection in self.selections:
            if selection.category == category:
                return selection
        return None

    def resolve(
        self,
        records: Iterable[dict[str, Any]],
        *,
        category_map: dict[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Apply the scope. Returns ``(kept, {category: withheld_by_scope})``.

        Runs on records that have already passed the transferability and consent
        gates, so a percentage is a percentage *of what was sellable* rather
        than of the raw store. Selling "100% of relationships" therefore never
        includes a record the seller withheld or a counterparty blocked, which
        is the reading a seller means and the only one that is safe.
        """
        # Relations are held out of the percentage entirely.
        #
        # An edge is not an independent thing a seller can offer half of; it is
        # a statement about two entities. Counting edges in the percentage
        # selects some whose endpoints were not selected, and the dangling-edge
        # prune then correctly discards them, so the buyer receives far less
        # than the listing promised. Measured on the seeded store, "50% of
        # relationships" produced *zero* relationship records that way.
        #
        # So edges pass through untouched here and are pruned downstream against
        # whatever entities actually survived. The percentage means what a
        # seller intends by it: half the counterparties, with the edges that
        # still make sense between them.
        buckets: dict[str, list[dict[str, Any]]] = {}
        relations: list[dict[str, Any]] = []
        for record in records:
            if record.get("kind") == "relation":
                relations.append(record)
                continue
            buckets.setdefault(route(record, category_map), []).append(record)

        kept: list[dict[str, Any]] = list(relations)
        withheld: dict[str, int] = {}

        for category, group in buckets.items():
            selection = self.selection_for(category)
            if selection is None:
                # Not part of the offer at all.
                withheld[category] = len(group)
                continue

            if selection.fingerprints:
                wanted = set(selection.fingerprints)
                chosen = [r for r in group if record_fingerprint(r) in wanted]
            else:
                # Newest first, ties broken on content hash.
                ordered = sorted(group, key=_sort_key, reverse=True)
                # Rounded up, so any non-zero percentage of a non-empty
                # category yields at least one record. A seller asking for 1%
                # of something means "a little", not "none".
                take = math.ceil(len(ordered) * selection.percent / 100)
                chosen = ordered[:take]

            kept.extend(chosen)
            if len(group) - len(chosen):
                withheld[category] = len(group) - len(chosen)

        return kept, withheld

    def to_dict(self) -> dict[str, Any]:
        return {
            "selections": [s.to_dict() for s in self.selections],
            "rule": (
                "Records are ordered newest first and a percentage takes that "
                "many from the front, rounded up. Ties break on content hash, "
                "never row id, so the buyer can reproduce the same selection."
            ),
        }


def take_inventory(
    source: Any, *, category_map: dict[str, str] | None = None
) -> dict[str, CategoryInventory]:
    """Read what a store actually holds, per category.

    Routed through the same map the export uses, so what a seller is shown here
    is exactly what a package would carry rather than a second opinion about it.
    """
    counts: dict[str, dict[str, Any]] = {
        category: {
            "sellable": 0,
            "withheld_by_seller": 0,
            "withheld_without_consent": 0,
            "stamps": [],
        }
        for category in DATA_CATEGORIES
    }

    for record in (
        *source.entities(),
        *source.archived(),
        *source.events(),
        *source.states(),
        *source.references(),
        *source.relations(),
    ):
        bucket = counts.setdefault(
            route(record, category_map),
            {
                "sellable": 0,
                "withheld_by_seller": 0,
                "withheld_without_consent": 0,
                "stamps": [],
            },
        )
        disclosure = read_disclosure(record.get("body"))
        if disclosure.may_transfer:
            bucket["sellable"] += 1
            stamp = record_timestamp(record)
            if stamp:
                bucket["stamps"].append(stamp)
        elif not disclosure.transferable:
            bucket["withheld_by_seller"] += 1
        else:
            bucket["withheld_without_consent"] += 1

    inventory: dict[str, CategoryInventory] = {}
    for category, bucket in counts.items():
        stamps: Sequence[str] = sorted(bucket["stamps"])
        inventory[category] = CategoryInventory(
            category=category,
            sellable=bucket["sellable"],
            withheld_by_seller=bucket["withheld_by_seller"],
            withheld_without_consent=bucket["withheld_without_consent"],
            newest=stamps[-1] if stamps else "",
            oldest=stamps[0] if stamps else "",
        )
    return inventory
