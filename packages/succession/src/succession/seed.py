"""A compact, entirely synthetic seller tenant.

Every persona, company, and number below is invented. The spec is explicit that
no real personal data belongs anywhere in this project, including in seed data
used only for local testing, and this module is the only place demo memory is
created — so that rule is enforceable by looking in one file.

Size is deliberately modest: a few dozen entities rather than thousands. The
free tier caps a local store at 5 MB (the SDK's ``FREE_TIER_CAP_BYTES``; the
build spec's 2 MB figure is out of date), and an export moves the entire store,
so a realistic-but-small seller is both truer to the demo and cheaper to move.

The shape tells a story on purpose: **Meridian Logistics Co.** is a freight
brokerage agent that has been running for about three months, has a handful of
repeat counterparties, has learned some habits about how each one likes to be
quoted, and is carrying two open commitments. That last part is what makes the
cutover beat real — the buyer's agent boots cold and picks up an in-flight quote
it has never seen.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .redaction import Sensitivity, mark

__all__ = ["seed_seller", "SELLER_AGENT_ID", "SEED_SUMMARY"]

SELLER_AGENT_ID = "erc8004:84532:0417"

_EPOCH = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)


def _ts(days: int, hours: int = 0) -> str:
    return (_EPOCH + timedelta(days=days, hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# (name, company, lane, cadence, note, sensitivity)
_COUNTERPARTIES = [
    ("northwind-mills", "Northwind Mills", "Duluth → Kansas City", "weekly",
     "Books Thursdays. Wants the quote before 10:00 local or it goes elsewhere.",
     Sensitivity.PUBLIC),
    ("cascade-orchards", "Cascade Orchards", "Yakima → Denver", "seasonal",
     "Reefer only. Will pay a premium for a same-day confirmation in harvest season.",
     Sensitivity.PRIVATE),
    ("harbor-point-ceramics", "Harbor Point Ceramics", "Tacoma → Boise", "monthly",
     "Fragile freight. Has refused two carriers over handling; only accepts the "
     "ones already on their approved list.",
     Sensitivity.PRIVATE),
    ("tallgrass-brewing", "Tallgrass Brewing", "Lincoln → Omaha", "biweekly",
     "Short haul, thin margin. Negotiates every time; settles about 4% under ask.",
     Sensitivity.REDACTED_PREVIEW_ONLY),
    ("selkirk-timber", "Selkirk Timber", "Coeur d'Alene → Spokane", "weekly",
     "Flatbed. Prefers a standing rate over per-load quoting.",
     Sensitivity.PUBLIC),
    ("bellweather-foods", "Bellweather Foods", "Fresno → Phoenix", "weekly",
     "Consolidator. Volume is real but payment terms run net-45.",
     Sensitivity.PRIVATE),
]

_PREFERENCES = [
    ("quoting-window", {"open_local": "07:30", "close_local": "16:00",
                        "note": "Quotes sent after 16:00 local convert at roughly half the rate."}),
    ("margin-floor", {"floor_pct": 9,
                      "note": "Below 9% the lane is not worth the carrier management overhead."}),
    ("carrier-shortlist", {"preferred": ["Two Rivers Freight", "Glacier Line", "Post Road Carriers"],
                           "note": "Ordered by on-time record over the last quarter."}),
    ("escalation", {"contact": "operations desk",
                    "note": "Anything over $6,000 or outside the shortlist goes to a human first."}),
]

_LEARNED = [
    ("thursday-booking-pattern",
     {"pattern": "Northwind Mills books Thursday mornings without exception.",
      "observed_count": 11,
      "action": "Pre-stage the Duluth → Kansas City quote Wednesday evening."}),
    ("reefer-premium-elasticity",
     {"pattern": "Cascade Orchards accepts up to a 14% premium during harvest, and "
                 "roughly 3% outside it.",
      "observed_count": 7,
      "action": "Anchor high in September, low in February."}),
    ("counter-then-settle",
     {"pattern": "Tallgrass Brewing counters every opening quote, then settles about "
                 "4% under ask.",
      "observed_count": 9,
      "action": "Open 4% above target rather than at target."}),
    ("net45-cash-drag",
     {"pattern": "Bellweather Foods' net-45 terms make nominally good lanes worse than "
                 "they look on margin alone.",
      "observed_count": 5,
      "action": "Apply a 2% terms adjustment before comparing against other lanes."}),
]

# The in-flight work. This is what the buyer's cold-booted agent must recall.
_COMMITMENTS = [
    ("quote-NW-4471",
     {"counterparty": "Northwind Mills",
      "lane": "Duluth → Kansas City",
      "quoted_rate_usd": 2380,
      "status": "open",
      "expires": _ts(92),
      "note": "Quoted Thursday morning. They asked for a hold through the weekend "
              "and have not yet confirmed."}),
    ("standing-rate-ST-0092",
     {"counterparty": "Selkirk Timber",
      "lane": "Coeur d'Alene → Spokane",
      "proposed_standing_rate_usd": 890,
      "status": "awaiting-countersignature",
      "note": "They agreed verbally to a standing rate and asked for it in writing."}),
]


def seed_seller(sink: Any, *, agent_identity: str = SELLER_AGENT_ID) -> dict[str, int]:
    """Populate ``sink`` with the synthetic seller tenant. Returns per-tier counts."""
    client = sink.client
    counts = {k: 0 for k in ("entity", "event", "state", "reference", "archived", "relation")}

    # -- identity ------------------------------------------------------
    client.set_entity(
        "identity",
        agent_identity,
        mark(
            {
                "name": "Meridian Logistics Co.",
                "role": "Freight brokerage agent",
                "erc8004": agent_identity,
                "registered_at": _ts(0),
                "operator_note": "Books and prices dry van, reefer, and flatbed lanes "
                                 "across the inland Northwest and upper Midwest.",
            },
            sensitivity=Sensitivity.PUBLIC,
        ),
    )
    counts["entity"] += 1

    # -- relationships -------------------------------------------------
    for slug, company, lane, cadence, note, sensitivity in _COUNTERPARTIES:
        client.set_entity(
            "relationship",
            slug,
            mark(
                {
                    "company": company,
                    "primary_lane": lane,
                    "cadence": cadence,
                    "note": note,
                    "first_seen": _ts(3),
                },
                sensitivity=sensitivity,
            ),
            status="active",
        )
        counts["entity"] += 1

    # One counterparty the seller is contractually barred from transferring.
    # This is the record that must never reach the Merkle tree.
    client.set_entity(
        "relationship",
        "ironwood-defense-logistics",
        mark(
            {
                "company": "Ironwood Defense Logistics",
                "primary_lane": "withheld",
                "note": "Under an NDA that forbids assignment. Excluded from any sale.",
            },
            sensitivity=Sensitivity.PRIVATE,
            transferable=False,
        ),
        status="active",
    )
    counts["entity"] += 1

    # -- preferences ---------------------------------------------------
    for name, body in _PREFERENCES:
        client.set_entity("preference", name, mark(body, sensitivity=Sensitivity.PRIVATE))
        counts["entity"] += 1

    # -- learned behaviors ---------------------------------------------
    for name, body in _LEARNED:
        client.set_entity(
            "learned-behavior", name, mark(body, sensitivity=Sensitivity.PRIVATE)
        )
        counts["entity"] += 1

    # -- commitments ---------------------------------------------------
    for name, body in _COMMITMENTS:
        client.set_entity(
            "commitment", name, mark(body, sensitivity=Sensitivity.PRIVATE), status="open"
        )
        counts["entity"] += 1

    # -- HOT state: the live working position --------------------------
    client.set_state(
        "current-negotiation",
        {
            "counterparty": "Northwind Mills",
            "commitment": "quote-NW-4471",
            "last_message_from_counterparty": "Can you hold 2380 through Monday?",
            "our_position": "Hold is fine through Monday 17:00. Below 2300 the lane "
                            "drops under the margin floor.",
            "opened_at": _ts(90, 2),
        },
    )
    counts["state"] += 1

    # -- REFERENCE: encoded playbook -----------------------------------
    client.set_reference(
        "skill/rate-negotiation",
        "Open 4% above target on repeat counterparties who habitually counter. "
        "Never go below the margin floor in preference/margin-floor. Escalate "
        "anything over $6,000 to the operations desk before committing.",
        metadata={"source": "learning-pass", "accepted_at": _ts(45)},
    )
    counts["reference"] += 1

    # -- COLD journal --------------------------------------------------
    journal = [
        (1, "registered with the ACP service registry"),
        (4, "opened relationship with Northwind Mills"),
        (6, "quoted Duluth → Kansas City at 2450; declined"),
        (7, "requoted Duluth → Kansas City at 2380; accepted"),
        (11, "opened relationship with Cascade Orchards"),
        (14, "quoted Yakima → Denver reefer at 3900; accepted"),
        (18, "opened relationship with Tallgrass Brewing"),
        (19, "quoted Lincoln → Omaha at 720; countered to 690; settled 695"),
        (23, "opened relationship with Selkirk Timber"),
        (26, "quoted Coeur d'Alene → Spokane at 910; accepted"),
        (31, "opened relationship with Harbor Point Ceramics"),
        (33, "quoted Tacoma → Boise at 1180; accepted with approved-carrier condition"),
        (38, "opened relationship with Bellweather Foods"),
        (40, "quoted Fresno → Phoenix at 1640; accepted on net-45 terms"),
        (44, "learning pass accepted skill reference/skill/rate-negotiation"),
        (51, "quoted Duluth → Kansas City at 2380; accepted"),
        (58, "quoted Lincoln → Omaha at 730; countered to 700; settled 702"),
        (63, "quoted Coeur d'Alene → Spokane at 890; accepted"),
        (69, "quoted Yakima → Denver reefer at 4100; accepted"),
        (74, "quoted Tacoma → Boise at 1210; accepted"),
        (79, "quoted Fresno → Phoenix at 1680; accepted"),
        (84, "Selkirk Timber proposed a standing rate; drafted at 890"),
        (90, "quoted Duluth → Kansas City at 2380; hold requested through Monday"),
    ]
    for day, action in journal:
        client.write_event(acted=[action], ts=_ts(day))
        counts["event"] += 1

    # -- ARCHIVE: a lapsed counterparty --------------------------------
    client.set_entity(
        "relationship",
        "pinecrest-paper",
        mark(
            {
                "company": "Pinecrest Paper",
                "primary_lane": "Missoula → Billings",
                "note": "Wound down operations in month two.",
            },
            sensitivity=Sensitivity.PRIVATE,
        ),
    )
    client.archive_entity("relationship", "pinecrest-paper", reason="counterparty closed")
    counts["archived"] += 1

    # -- WARM edges ----------------------------------------------------
    edges = [
        (("commitment", "quote-NW-4471"), ("relationship", "northwind-mills"), "quoted-to"),
        (("commitment", "standing-rate-ST-0092"), ("relationship", "selkirk-timber"), "quoted-to"),
        (("learned-behavior", "thursday-booking-pattern"), ("relationship", "northwind-mills"), "learned-from"),
        (("learned-behavior", "counter-then-settle"), ("relationship", "tallgrass-brewing"), "learned-from"),
        (("learned-behavior", "reefer-premium-elasticity"), ("relationship", "cascade-orchards"), "learned-from"),
        (("learned-behavior", "net45-cash-drag"), ("relationship", "bellweather-foods"), "learned-from"),
    ]
    counts["relation"] += _write_edges(client, edges)

    return counts


def _write_edges(client: Any, edges: list[tuple[tuple[str, str], tuple[str, str], str]]) -> int:
    """Write entity_relations rows directly — the client has no public edge API."""
    import uuid

    tenant = client.get_tenant()
    written = 0
    with client.storage.transaction() as conn:
        for (f_cat, f_name), (t_cat, t_name), rel in edges:
            f = conn.execute(
                "SELECT id FROM entities WHERE tenant_id=? AND category=? AND name=?",
                (tenant, f_cat, f_name),
            ).fetchone()
            t = conn.execute(
                "SELECT id FROM entities WHERE tenant_id=? AND category=? AND name=?",
                (tenant, t_cat, t_name),
            ).fetchone()
            if f is None or t is None:
                continue
            conn.execute(
                "INSERT INTO entity_relations (id, tenant_id, from_id, to_id, relation_type) "
                "VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, tenant, f["id"], t["id"], rel),
            )
            written += 1
    return written


SEED_SUMMARY = {
    "agent": "Meridian Logistics Co.",
    "counterparties": len(_COUNTERPARTIES),
    "non_transferable": 1,
    "open_commitments": len(_COMMITMENTS),
}
