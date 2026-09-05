"""Reputation that belongs to the memory rather than to a wallet.

The problem this solves
-----------------------

An agent's standing normally lives with an account: a registry entry, a wallet,
a platform profile. None of that survives a sale, so a buyer inherits a working
memory with no way to show what it has been through, and every lineage restarts
from nothing however good its history was.

What travels instead is evidence. Every completed transfer appends an entry to
the provenance chain, and that entry is only written when settlement actually
verified, so the chain *is* an integrity record: a lineage five owners deep is
five hash comparisons that matched, each one signed and each one settled on
chain. The job history the agent accumulated is already inside the memory as
hashed records. The memory's own version number says whether each owner grew it
or let it sit.

So reputation here is not a number somebody stores. It is **recomputed from the
package by whoever is looking at it**, exactly the way the integrity root is
recomputed rather than trusted. That is the whole design, and it is what makes
the score worth anything:

* A seller cannot inflate it, because they do not supply it.
* A buyer verifies it the same way they verify the memory, from the bytes they
  received.
* It cannot be faked into existence before a market exists, because every input
  is either a signed chain entry, an on-chain settlement, or a record already
  covered by the Merkle tree.

What it deliberately is not
---------------------------

There is no ``buyer_satisfaction`` term and no cross-marketplace aggregate.
Both need transaction volume that does not exist yet, and inventing them would
be exactly the fabrication this project refuses everywhere else. When there is
real volume they belong here; until then their absence is the honest reading.

The score is also not a *price*. :mod:`succession.valuation` prices the asset;
this describes its track record. A memory can be valuable and unproven, or
modest and impeccable, and collapsing the two would hide the difference a buyer
most needs to see.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Sequence

__all__ = [
    "Factor",
    "Reputation",
    "LineageLink",
    "read_lineage",
    "score_lineage",
    "score_package",
]

_D = Decimal


def _q(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(_D(places), rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, low: Decimal = _D("0"), high: Decimal = _D("1")) -> Decimal:
    return max(low, min(high, value))


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return None


# --- weights -------------------------------------------------------------
#
# Named constants rather than inline numbers, because a reputation score whose
# weights are buried in an expression is a score nobody can argue with. These
# sum to 1; the result is scaled to 100 at the end.

W_INTEGRITY = _D("0.34")   # transfers that verified
W_LINEAGE = _D("0.22")     # how many times it has changed hands intact
W_CONTINUITY = _D("0.18")  # whether owners grew it or sat on it
W_EARNINGS = _D("0.16")    # settled ACP outcomes carried in memory
W_SPAN = _D("0.10")        # how long the lineage has existed

#: A lineage is "established" at this many verified handovers. Chosen low on
#: purpose: the difference between one careful transfer and three is real, and
#: the difference between eight and eleven is noise.
LINEAGE_TARGET = _D("3")

#: Custody span, in days, at which the span factor saturates.
SPAN_TARGET_DAYS = _D("365")

#: Below this many resolved ACP outcomes the earnings factor abstains rather
#: than scoring, matching the same floor the valuation uses.
MIN_RESOLVED = 5


@dataclass(frozen=True)
class Factor:
    """One component of the score, with the inputs it was computed from."""

    name: str
    value: Decimal
    weight: Decimal
    inputs: dict[str, Any]
    explanation: str

    @property
    def contribution(self) -> Decimal:
        return self.value * self.weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": str(_q(self.value)),
            "weight": str(_q(self.weight)),
            "contribution": str(_q(self.contribution)),
            "inputs": self.inputs,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class LineageLink:
    """One verified change of hands, read out of the provenance chain."""

    owner: str
    acquired_at: str
    verified_hash: str
    memory_version: int | None = None

    @property
    def well_formed(self) -> bool:
        """Whether this entry carries what a verifier needs to trust it.

        A link without an owner or a hash is not evidence of anything, and
        counting it would let a malformed chain score the same as a sound one.
        """
        return bool(self.owner) and self.verified_hash.startswith("0x") and len(
            self.verified_hash
        ) == 66


@dataclass(frozen=True)
class Reputation:
    """A recomputed opinion of a lineage's track record."""

    score: Decimal
    grade: str
    factors: tuple[Factor, ...]
    links: int
    computed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": str(_q(self.score, "0.01")),
            "grade": self.grade,
            "links": self.links,
            "factors": [f.to_dict() for f in self.factors],
            "computed_at": self.computed_at,
            "basis": (
                "Recomputed from the provenance chain and the memory itself. "
                "Not supplied by the seller and not stored anywhere; a buyer "
                "derives the same figure from the package they received."
            ),
        }


def _grade(score: Decimal) -> str:
    """A word for the number.

    Bands rather than a bare figure because 71 and 74 are not different
    findings, and presenting them as though they were invites false precision.
    """
    if score >= 80:
        return "established"
    if score >= 60:
        return "proven"
    if score >= 40:
        return "developing"
    if score > 0:
        return "early"
    return "unproven"


def read_lineage(chain: Sequence[dict[str, Any]] | None) -> list[LineageLink]:
    """Parse a provenance chain into links. Tolerates entries from older exports.

    ``memory_version`` was added to chain entries after the first transfers
    settled, so a link that predates it is carried with ``None`` rather than
    dropped: the continuity factor abstains on it instead of scoring it zero,
    which would punish a lineage for the format's age rather than its conduct.
    """
    links: list[LineageLink] = []
    for entry in chain or []:
        if not isinstance(entry, dict):
            continue
        version = entry.get("memory_version")
        links.append(
            LineageLink(
                owner=str(entry.get("owner", "")),
                acquired_at=str(entry.get("acquired_at", "")),
                verified_hash=str(entry.get("verified_hash", "")),
                memory_version=int(version) if isinstance(version, int) else None,
            )
        )
    return links


def score_lineage(
    links: Sequence[LineageLink],
    *,
    resolved_jobs: int = 0,
    completed_jobs: int = 0,
    current_version: int | None = None,
    now: datetime | None = None,
) -> Reputation:
    """Score a lineage from its links and the memory's own counters.

    Every argument is something a holder of the package can read for themselves.
    Nothing here is passed in by a seller.
    """
    now = now or datetime.now(timezone.utc)
    sound = [link for link in links if link.well_formed]
    factors: list[Factor] = []

    # --- integrity -------------------------------------------------------
    # A chain entry exists only because a settlement verified, so the ratio of
    # well-formed entries to total entries is the record of whether every hand
    # this memory passed through left a checkable trace.
    if links:
        integrity = _D(len(sound)) / _D(len(links))
        integrity_note = (
            f"{len(sound)} of {len(links)} chain entries carry a complete, "
            "well-formed verification record."
        )
    else:
        # An origin memory has never been transferred. That is not a failing and
        # not an achievement; it scores neutral so a first sale is neither
        # penalised nor credited for a history it does not have.
        integrity = _D("0.5")
        integrity_note = (
            "No transfers yet. Integrity is unproven rather than poor, so this "
            "scores neutral."
        )
    factors.append(
        Factor(
            "integrity_record",
            _clamp(integrity),
            W_INTEGRITY,
            {"sound_links": len(sound), "total_links": len(links)},
            integrity_note,
        )
    )

    # --- lineage depth ---------------------------------------------------
    depth = _clamp(_D(len(sound)) / LINEAGE_TARGET)
    factors.append(
        Factor(
            "lineage_depth",
            depth,
            W_LINEAGE,
            {"verified_handovers": len(sound), "saturates_at": int(LINEAGE_TARGET)},
            f"{len(sound)} verified handover(s); the factor saturates at "
            f"{int(LINEAGE_TARGET)} because the difference between one and three "
            "is real and the difference between eight and eleven is noise.",
        )
    )

    # --- continuity ------------------------------------------------------
    # Did each owner add to the memory, or buy it and let it sit? Read from the
    # version recorded at each handover against the version now.
    versions = [link.memory_version for link in sound if link.memory_version is not None]
    if versions and current_version is not None:
        grew = current_version > max(versions)
        growth = _D(max(0, current_version - max(versions)))
        # Saturates quickly: any real growth is the signal; the amount is not.
        continuity = _clamp(growth / _D("20")) if grew else _D("0.25")
        continuity_note = (
            f"Memory version {current_version} against {max(versions)} at the last "
            f"handover: {'grown' if grew else 'unchanged'} under the current owner."
        )
    else:
        continuity = _D("0.5")
        continuity_note = (
            "No versioned handover to compare against, so continuity abstains "
            "rather than scoring."
        )
    factors.append(
        Factor(
            "continuity",
            continuity,
            W_CONTINUITY,
            {
                "current_version": current_version,
                "version_at_last_handover": max(versions) if versions else None,
            },
            continuity_note,
        )
    )

    # --- earnings --------------------------------------------------------
    # Settled ACP outcomes, already inside the memory and covered by the tree.
    if resolved_jobs >= MIN_RESOLVED:
        earnings = _clamp(_D(completed_jobs) / _D(resolved_jobs))
        earnings_note = (
            f"{completed_jobs} of {resolved_jobs} settled outcomes completed."
        )
    else:
        earnings = _D("0.5")
        earnings_note = (
            f"Only {resolved_jobs} settled outcome(s); below {MIN_RESOLVED} this "
            "abstains rather than scoring, because a rate over three jobs is not "
            "a rate."
        )
    factors.append(
        Factor(
            "earnings_record",
            earnings,
            W_EARNINGS,
            {"completed": completed_jobs, "resolved": resolved_jobs},
            earnings_note,
        )
    )

    # --- custody span ----------------------------------------------------
    first = next((_parse(link.acquired_at) for link in sound if _parse(link.acquired_at)), None)
    if first:
        days = _D(str(max((now - first).total_seconds(), 0))) / _D("86400")
        span = _clamp(days / SPAN_TARGET_DAYS)
        span_note = f"The lineage has existed for {int(days)} day(s)."
    else:
        days = _D("0")
        span = _D("0")
        span_note = "No dated handover, so the lineage has no measurable span yet."
    factors.append(
        Factor(
            "custody_span",
            span,
            W_SPAN,
            {"days": int(days), "saturates_at_days": int(SPAN_TARGET_DAYS)},
            span_note,
        )
    )

    total = sum((f.contribution for f in factors), _D("0")) * _D("100")
    return Reputation(
        score=_q(total, "0.01"),
        grade=_grade(total),
        factors=tuple(factors),
        links=len(links),
        computed_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def score_package(package: Any, *, now: datetime | None = None) -> Reputation:
    """Score an SMP package. This is the call a buyer makes to check for themselves.

    Everything it reads is inside the package they were handed and covered by
    the integrity root, so a seller cannot present one reputation and deliver
    another any more than they can present one memory and deliver another.
    """
    header = getattr(package, "header", {}) or {}
    links = read_lineage(header.get("provenance_chain"))

    completed = resolved = 0
    for record in _acp_records(package):
        phase = str(record.get("phase", "")).upper()
        if phase in ("COMPLETED", "COMPLETE"):
            completed += 1
            resolved += 1
        elif phase in ("REJECTED", "CANCELLED", "EXPIRED", "FAILED"):
            resolved += 1

    return score_lineage(
        links,
        resolved_jobs=resolved,
        completed_jobs=completed,
        current_version=header.get("memory_version"),
        now=now,
    )


def _acp_records(package: Any) -> list[dict[str, Any]]:
    """Job records carried in the package's history directory.

    Read defensively: a package with no ACP integration is the normal case, not
    an error, and the earnings factor abstains on it.
    """
    data = getattr(package, "data", {}) or {}
    out = []
    for record in data.get("history", []) or []:
        body = record.get("body") if isinstance(record, dict) else None
        if isinstance(body, dict) and ("phase" in body or "job_id" in body):
            out.append(body)
    return out
