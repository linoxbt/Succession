"""Demo listings, and the wall between them and the real market.

Six real listings exist on Base Sepolia and five of them carry a published data
room. They are true, and they are small: forty-nine records apiece, from a
seller tenant that was seeded to prove a transfer works rather than to look like
a going concern. A marketplace showing only those reads as an empty room.

So this module supplies a handful of richer listings for the screen to be judged
against. Every one of them is a lie by construction, and the design here is
about making that lie impossible to mistake or to launder:

* Every row carries ``demo: true``, and the UI is required to stamp it.
* Every listing id begins with ``demo-``, so a row's provenance is legible from
  its identifier alone in a log, a URL or a database.
* The seller address is the zero address. There is no key behind it, so no chain
  write can ever be authorised against one of these.
* They are appended to the *listing collection* only. Totals, volumes, agent and
  seller counts and the capability model are computed from real rows before
  these are added, so no aggregate on any screen counts a fiction. A test
  asserts exactly that.

The pattern is borrowed from ``walkthrough.py``, which has stamped every
response ``simulated: true`` since the scripted sale existed, and which has a
test asserting the real marketplace stays empty even after it settles.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DEMO_PREFIX", "demo_rows", "is_demo"]

#: Every demo listing id starts with this. `is_demo` is the only check anything
#: else should use, so the convention has one enforcement point.
DEMO_PREFIX = "demo-"

#: No private key produces this address, so a demo listing cannot be bought,
#: cancelled or settled even if the UI forgot to disable the button.
_NOBODY = "0x0000000000000000000000000000000000000000"

_NOTICE = (
    "Demonstration listing. Not on chain, not for sale, and excluded from every "
    "figure this marketplace reports."
)


def is_demo(listing_id: str) -> bool:
    """Whether a listing id belongs to the demo set."""
    return listing_id.startswith(DEMO_PREFIX)


def _valuation(base: str, amount: str, factors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "currency": "USD",
        "base_price": base,
        "amount": amount,
        "factors": factors,
        "formula": (
            "base_price × tenure_factor × interaction_density × "
            "relationship_breadth × task_performance × recency_weight"
        ),
        "excluded": {
            "buyer_demand": "v2, needs real marketplace volume",
            "origin_reputation": "v2, needs a lineage history to draw on",
            "buyer_satisfaction": "v2, measurable only after transfers complete",
        },
    }


def _factor(name: str, value: str, inputs: dict[str, Any], explanation: str) -> dict[str, Any]:
    return {"name": name, "value": value, "inputs": inputs, "explanation": explanation}


def _inventory(counts: dict[str, tuple[int, int, int]]) -> dict[str, dict[str, Any]]:
    """Build a per-directory inventory from (sellable, by_seller, no_consent)."""
    out: dict[str, dict[str, Any]] = {}
    for category, (sellable, by_seller, no_consent) in counts.items():
        total = sellable + by_seller + no_consent
        if sellable == 0:
            depth = "empty"
        elif sellable < 5:
            depth = "thin"
        elif sellable < 20:
            depth = "moderate"
        else:
            depth = "deep"
        out[category] = {
            "category": category,
            "sellable": sellable,
            "withheld_by_seller": by_seller,
            "withheld_without_consent": no_consent,
            "total": total,
            "depth": depth,
            "offerable": sellable > 0,
            "newest": "",
            "oldest": "",
        }
    return out


def _transferability(inventory: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        name: {
            "sellable": row["sellable"],
            "withheld": row["withheld_by_seller"] + row["withheld_without_consent"],
        }
        for name, row in inventory.items()
    }


def _row(
    *,
    listing_id: str,
    agent_id: str,
    name: str,
    vertical: str,
    price: int,
    state: str,
    tenure_days: int,
    counts: dict[str, tuple[int, int, int]],
    events: int,
    counterparties: int,
    completed: int,
    failed: int,
    valuation_amount: str,
    root: str,
    reputation: dict[str, Any] | None,
) -> dict[str, Any]:
    inventory = _inventory(counts)
    sellable = sum(row["sellable"] for row in inventory.values())
    withheld = sum(row["withheld_without_consent"] for row in inventory.values())
    resolved = completed + failed
    rate = f"{completed / resolved:.4f}" if resolved >= 5 else None

    preview = {
        "agent_identity": agent_id,
        "tenure_days": tenure_days,
        "counts": {"total_records": sellable + withheld},
        "memory_size_bytes": sellable * 1_180,
        "category_breakdown": {},
        "public_counterparties": [],
        "withheld_non_transferable": withheld,
        "category_transferability": _transferability(inventory),
        "inventory": inventory,
        "reputation": reputation,
        "disclosure": (
            "Aggregate statistics only. Record contents are released after "
            "purchase and hash verification."
        ),
        "committed_root": root,
        "acp": {
            "agent_address": _NOBODY,
            "agent_id": None,
            "agent_name": name,
            "registered": False,
            "source": "recorded",
            "fetched_at": "",
            "completed_jobs": completed,
            "failed_jobs": failed,
            "gross_volume": "0",
            "distinct_counterparties": counterparties,
            "success_rate": rate,
            "verifiable_job_ids": [],
            "verification": _NOTICE,
        },
        "provenance_of_figures": {
            "self_reported": [
                "counts",
                "memory_size_bytes",
                "category_breakdown",
                "tenure_days",
            ],
            "independently_verifiable": [],
        },
        "valuation": _valuation(
            "200.00",
            valuation_amount,
            [
                _factor(
                    "tenure_factor",
                    f"{min(2.0, max(0.5, tenure_days / 180)):.4f}",
                    {"tenure_days": f"{tenure_days}.00"},
                    "Custody age against a 180 day target, clamped to [0.5, 2.0].",
                ),
                _factor(
                    "interaction_density",
                    f"{min(2.0, max(0.5, (events / max(tenure_days, 1)) / 0.25)):.4f}",
                    {
                        "events": events,
                        "events_per_day": f"{events / max(tenure_days, 1):.4f}",
                    },
                    "Journal events per day against a 0.25 target, clamped to [0.5, 2.0].",
                ),
                _factor(
                    "relationship_breadth",
                    f"{min(2.0, max(0.6, 0.6 + counterparties * 0.12)):.4f}",
                    {"distinct_counterparties": counterparties},
                    "Distinct counterparties at 0.12 each, clamped to [0.6, 2.0].",
                ),
                _factor(
                    "task_performance",
                    f"{0.5 + (completed / resolved if resolved else 0.5):.4f}",
                    {
                        "trust_score": f"{completed / resolved:.2f}" if resolved else "0.50",
                        "basis": "journal",
                        "wins": completed,
                        "losses": failed,
                        "resolved": resolved,
                    },
                    "Resolved outcomes mapped onto [0.5, 1.5]; abstains below five.",
                ),
                _factor(
                    "recency_weight",
                    "1.0000",
                    {"days_since_last_write": "1.00"},
                    "Fresh within 7 days, decaying to 0.4 at 90, clamped to [0.4, 1.0].",
                ),
            ],
        ),
    }

    return {
        "listing": {
            "listing_id": listing_id,
            "agent_id": agent_id.rsplit(":", 1)[-1],
            "seller": _NOBODY,
            "seller_signature": "",
            "hash_commitment": root,
            "price": price,
            "currency": "USDC",
            "categories": [c for c, row in inventory.items() if row["offerable"]],
            "valuation_reference": valuation_amount,
            "state": state,
            "buyer": "",
            "escrow_balance": price if state == "escrowed" else 0,
            "delivered_hash": root if state == "confirmed" else "",
            "sealed": state == "confirmed",
            "created_at": "",
            "settled_at": "",
        },
        "preview": preview,
        "name": name,
        "vertical": vertical,
        "valuation": valuation_amount,
        "agent_identity": agent_id,
        "has_envelope": False,
        "has_metadata": True,
        # The two fields the UI keys on. `demo` gates every write path and every
        # aggregate; `notice` is what the row says about itself on screen.
        "demo": True,
        "notice": _NOTICE,
        "integrity": {},
        "provenance": {},
    }


def demo_rows() -> list[dict[str, Any]]:
    """The demo listings, freshly built so no caller can mutate the source."""
    return [
        _row(
            listing_id="demo-freight-01",
            agent_id="erc8004:84532:9001",
            name="Northwest Freight Desk",
            vertical="Freight brokerage",
            price=8_400_000,
            state="open",
            tenure_days=337,
            counts={
                "identity": (4, 0, 0),
                "relationships": (382, 12, 41),
                "preferences": (147, 3, 0),
                "history": (1_842, 0, 0),
                "commitments": (61, 9, 4),
                "learned-behaviors": (93, 0, 0),
            },
            events=1_842,
            counterparties=382,
            completed=1_204,
            failed=74,
            valuation_amount="8412.60",
            root="0x8f3a2c7d41b6e05938ac4d1e77b20f6c5a9e83d47c1b0629fe5a8437d90c2b16",
            reputation={
                "score": "71.40",
                "grade": "proven",
                "links": 2,
                "computed_at": "",
                "basis": _NOTICE,
                "factors": [
                    {
                        "name": "integrity_record",
                        "value": "1.0000",
                        "weight": "0.3400",
                        "contribution": "0.3400",
                        "inputs": {"sound_links": 2, "total_links": 2},
                        "explanation": "Both recorded handovers carry a well formed root.",
                    },
                    {
                        "name": "lineage_depth",
                        "value": "0.6667",
                        "weight": "0.2200",
                        "contribution": "0.1467",
                        "inputs": {"verified_handovers": 2, "saturates_at": 3},
                        "explanation": "Two verified handovers against a target of three.",
                    },
                    {
                        "name": "continuity",
                        "value": "0.8000",
                        "weight": "0.1800",
                        "contribution": "0.1440",
                        "inputs": {"current_version": 41, "version_at_last_handover": 33},
                        "explanation": "The memory grew by eight versions since it changed hands.",
                    },
                    {
                        "name": "earnings_record",
                        "value": "0.9421",
                        "weight": "0.1600",
                        "contribution": "0.1507",
                        "inputs": {"completed": 1204, "resolved": 1278},
                        "explanation": "Completed against resolved outcomes, abstaining below five.",
                    },
                    {
                        "name": "custody_span",
                        "value": "0.9233",
                        "weight": "0.1000",
                        "contribution": "0.0923",
                        "inputs": {"days": 337, "saturates_at_days": 365},
                        "explanation": "Custody age against a one year saturation point.",
                    },
                ],
            },
        ),
        _row(
            listing_id="demo-research-02",
            agent_id="erc8004:84532:9002",
            name="DeFi Research Desk",
            vertical="Protocol research",
            price=12_600_000,
            state="escrowed",
            tenure_days=214,
            counts={
                "identity": (3, 0, 0),
                "relationships": (118, 4, 22),
                "preferences": (86, 0, 0),
                "history": (2_930, 0, 0),
                "commitments": (12, 2, 0),
                "learned-behaviors": (241, 7, 0),
            },
            events=2_930,
            counterparties=118,
            completed=402,
            failed=11,
            valuation_amount="12603.18",
            root="0x2d61b04fae9c3785012f6d8b4ac7e1930fd52c86b7419ae0538c214d6f0b93ea",
            reputation=None,
        ),
        _row(
            listing_id="demo-support-03",
            agent_id="erc8004:84532:9003",
            name="Tier One Support Agent",
            vertical="Customer operations",
            price=3_100_000,
            state="confirmed",
            tenure_days=96,
            counts={
                "identity": (2, 0, 0),
                "relationships": (54, 0, 8),
                "preferences": (31, 0, 0),
                "history": (612, 0, 0),
                "commitments": (7, 0, 0),
                "learned-behaviors": (44, 0, 0),
            },
            events=612,
            counterparties=54,
            completed=188,
            failed=27,
            valuation_amount="3097.44",
            root="0xb7c40e29d8163fa5e02b917c46d3850af1629bd74e0c58a3927fb6041ec8d253",
            reputation=None,
        ),
    ]
