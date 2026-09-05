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
    "Consent",
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


class Consent:
    """On what basis a record describing someone else may change hands.

    Relationship records describe real counterparties, and until now the
    package answered that question with a single sentence asserting the seller
    had authority. An assertion is not a mechanism: it applies equally to every
    record, so a seller with a defensible basis for most of their book and none
    for the rest had no way to say so, and a buyer had no way to see it.

    This is per record and it is enforced, not declared. ``WITHHELD`` is the one
    that does work: it is filtered before hashing, exactly like
    ``transferable: false``, so a record whose counterparty has not agreed to
    the transfer never enters the Merkle tree in recoverable form.

    The vocabulary deliberately mirrors the lawful bases an operator would
    already be reasoning about, so the flag maps onto a real answer rather than
    inventing a private taxonomy. It does not make that answer *correct* — that
    remains the operator's judgement against their own terms, and no library can
    supply it.
    """

    CONTRACTUAL = "contractual"
    LEGITIMATE_INTEREST = "legitimate-interest"
    EXPLICIT = "explicit"
    WITHHELD = "withheld"

    ALL = (CONTRACTUAL, LEGITIMATE_INTEREST, EXPLICIT, WITHHELD)

    #: The bases under which a record may move. Anything else is withheld.
    TRANSFERABLE = (CONTRACTUAL, LEGITIMATE_INTEREST, EXPLICIT)


@dataclass(frozen=True)
class Disclosure:
    """One record's disclosure posture."""

    sensitivity: str = Sensitivity.PRIVATE
    transferable: bool = True
    consent: str = Consent.CONTRACTUAL

    @property
    def may_transfer(self) -> bool:
        """Both gates, together.

        `transferable` is the seller's own decision about their asset; `consent`
        is about the third party the record describes. A record needs to clear
        both, and either one alone can stop it.
        """
        return self.transferable and self.consent in Consent.TRANSFERABLE

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
        return self.may_transfer


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
    consent = meta.get("consent", Consent.CONTRACTUAL)
    if consent not in Consent.ALL:
        raise ValueError(
            f"unknown consent basis {consent!r}; expected one of {Consent.ALL}"
        )
    return Disclosure(
        sensitivity=sensitivity, transferable=transferable, consent=consent
    )


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
    consent: str | None = None,
) -> dict[str, Any]:
    """Return a copy of ``body`` with disclosure flags set. Seller-side helper."""
    if sensitivity is not None and sensitivity not in Sensitivity.ALL:
        raise ValueError(f"unknown sensitivity {sensitivity!r}")
    if consent is not None and consent not in Consent.ALL:
        raise ValueError(f"unknown consent basis {consent!r}")
    meta = dict(body.get(RESERVED_KEY) or {}) if isinstance(body, dict) else {}
    if sensitivity is not None:
        meta["sensitivity"] = sensitivity
    if transferable is not None:
        meta["transferable"] = transferable
    if consent is not None:
        meta["consent"] = consent
    return {**body, RESERVED_KEY: meta}


@dataclass(frozen=True)
class RedactionReport:
    """What the filter removed. Ships in the package's ``permissions/`` directory.

    Counts only — naming a withheld entity would defeat the point of
    withholding it.
    """

    withheld_non_transferable: int = 0
    withheld_without_consent: int = 0
    withheld_by_category_filter: int = 0
    withheld_dangling_relations: int = 0
    categories_selected: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "withheld_non_transferable": self.withheld_non_transferable,
            "withheld_by_category_filter": self.withheld_by_category_filter,
            "withheld_without_consent": self.withheld_without_consent,
            "withheld_dangling_relations": self.withheld_dangling_relations,
            "categories_selected": list(self.categories_selected),
        }


def filter_transferable(
    records: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    """Drop what may not move. Returns ``(kept, withheld_flag, withheld_consent)``.

    This is the gate that runs before serialization, and therefore before
    hashing: a record stopped here never enters the Merkle tree in recoverable
    form, rather than being hidden at display time.

    The two withheld counts are reported separately because they answer
    different questions. ``withheld_flag`` is the seller withholding part of
    their own asset. ``withheld_consent`` is a record about a third party that
    has no basis to move, which is a fact about the counterparty rather than a
    choice by the seller, and a buyer reading the permissions document should
    be able to tell the two apart.
    """
    kept: list[dict[str, Any]] = []
    withheld_flag = 0
    withheld_consent = 0
    for record in records:
        disclosure = read_disclosure(record.get("body"))
        if disclosure.may_transfer:
            kept.append(record)
        elif not disclosure.transferable:
            withheld_flag += 1
        else:
            withheld_consent += 1
    return kept, withheld_flag, withheld_consent
