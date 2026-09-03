"""The redacted preview a buyer sees before paying.

Aggregate statistics only. No record body, no counterparty name, no journal
text ever crosses this boundary — not truncated, not snippeted, not hashed in a
form anyone could grind. The rule the spec sets is that no code path in the
preview can leak private or non-transferable entity content, and the way to
keep that true as the code changes is to make the preview *constructed from
counts*, so there is no body in scope to leak by accident.

Two filters run before anything is counted:

* non-transferable records are dropped entirely — they are not part of the
  asset, and counting them would overstate what is for sale;
* everything else contributes to counts, but only ``public`` records may
  contribute a *name* to the small sample of counterparties shown.

That second point is the one real disclosure decision in here. A buyer with
nothing but numbers cannot tell a brokerage from a barber shop, so the preview
shows the handful of counterparties the seller explicitly marked ``public`` —
their own choice, made per record, in their listing flow.

Everything above is computed from the seller's own memory, which makes it
**self-reported**. The ACP job history carried alongside it is not: each entry
resolves to an on-chain job id against the ACP contract on Base, so a buyer can
re-derive those counts without trusting the seller at all. The preview keeps the
two clearly separated and labelled rather than blending them into one number,
because a buyer's confidence in each should be different.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .canonical import canonical_bytes
from .memory.base import MemorySource
from .redaction import Sensitivity, read_disclosure
from .valuation import Valuation, value_tenant

__all__ = ["DataRoomPreview", "build_preview"]


@dataclass(frozen=True)
class DataRoomPreview:
    agent_identity: str
    tenure_days: int
    counts: dict[str, int]
    memory_size_bytes: int
    category_breakdown: dict[str, int]
    public_counterparties: tuple[str, ...]
    withheld_non_transferable: int
    valuation: Valuation | None = None
    committed_root: str | None = None
    acp: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "agent_identity": self.agent_identity,
            "tenure_days": self.tenure_days,
            "counts": dict(self.counts),
            "memory_size_bytes": self.memory_size_bytes,
            "category_breakdown": dict(self.category_breakdown),
            "public_counterparties": list(self.public_counterparties),
            "withheld_non_transferable": self.withheld_non_transferable,
            "disclosure": (
                "Aggregate statistics only. Record contents are released after "
                "purchase and hash verification."
            ),
        }
        if self.valuation is not None:
            out["valuation"] = self.valuation.to_dict()
        if self.committed_root is not None:
            out["committed_root"] = self.committed_root
        out["acp"] = self.acp
        out["provenance_of_figures"] = {
            "self_reported": [
                "counts",
                "memory_size_bytes",
                "category_breakdown",
                "tenure_days",
            ],
            "independently_verifiable": (
                ["acp"] if self.acp and self.acp.get("registered") else []
            ),
        }
        return out


def build_preview(
    source: MemorySource,
    *,
    agent_identity: str,
    committed_root: str | None = None,
    base_price: Decimal | str | int | None = None,
    now: datetime | None = None,
    sample_limit: int = 5,
    acp_history: Any = None,
) -> DataRoomPreview:
    """Compute the pre-purchase preview. Counts in, counts out.

    ``acp_history`` defaults to whatever the tenant itself carries, because a
    synced agent's job history is part of its memory. Passing one explicitly
    overrides that — the listing flow does so with freshly fetched history.
    """
    now = now or datetime.now(timezone.utc)

    if acp_history is None:
        from .acp import job_history_from_memory

        acp_history = job_history_from_memory(source)
        if not acp_history.jobs and not acp_history.registered:
            acp_history = None

    entities = [
        e for e in source.entities() if read_disclosure(e["body"]).transferable
    ]
    archived = [
        a for a in source.archived() if read_disclosure(a["body"]).transferable
    ]
    withheld = (len(source.entities()) - len(entities)) + (
        len(source.archived()) - len(archived)
    )
    events = source.events()
    states = source.states()
    references = source.references()
    relations = source.relations()

    # Size is measured over the canonical serialization of what is actually for
    # sale, not the SQLite file on disk. A buyer comparing two listings should
    # be comparing memory, not page fragmentation and index overhead.
    size = sum(
        len(canonical_bytes(r.get("body")))
        for r in (*entities, *archived, *states)
        if r.get("body") is not None
    ) + sum(len(canonical_bytes(e)) for e in events)

    stamps = sorted(e["ts"] for e in events if e.get("ts"))
    if stamps:
        first = datetime.strptime(stamps[0][:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        tenure_days = max((now - first).days, 0)
    else:
        tenure_days = 0

    breakdown: dict[str, int] = {}
    for entity in entities:
        breakdown[entity["category"]] = breakdown.get(entity["category"], 0) + 1

    public_names = tuple(
        sorted(
            e["name"]
            for e in entities
            if e["category"] == "relationship"
            and read_disclosure(e["body"]).sensitivity == Sensitivity.PUBLIC
        )
    )[:sample_limit]

    valuation = value_tenant(
        source,
        now=now,
        acp_history=acp_history,
        **({"base_price": base_price} if base_price is not None else {}),
    )

    return DataRoomPreview(
        agent_identity=agent_identity,
        tenure_days=tenure_days,
        counts={
            "entities": len(entities),
            "journal_events": len(events),
            "state_documents": len(states),
            "reference_documents": len(references),
            "archived_entities": len(archived),
            "relations": len(relations),
            "total_records": len(entities)
            + len(events)
            + len(states)
            + len(references)
            + len(archived)
            + len(relations),
        },
        memory_size_bytes=size,
        category_breakdown=dict(sorted(breakdown.items())),
        public_counterparties=public_names,
        withheld_non_transferable=withheld,
        valuation=valuation,
        committed_root=committed_root,
        acp=acp_history.to_dict() if acp_history is not None else None,
    )
