"""The marketplace population — several genuinely different agents.

A marketplace with one listing is a detail page, so this seeds a handful of
distinct agents for it. Every persona and company here is invented, like the
rest of the demo data, and the rule from :mod:`succession.seed` holds: no real
personal data appears anywhere in this project.

**What is not invented is any figure the marketplace displays.** Each archetype
is written into a real Sibyl tenant, exported through the real pipeline, and
hashed with the real Merkle tree — so its committed root, record count, memory
size and valuation are all computed, not typed. That distinction is the whole
point. A marketplace showing twelve hardcoded "agents for sale" with plausible
prices is precisely the pattern this project exists to argue against; a
marketplace showing six real exports of six real stores is evidence.

The archetypes differ along the axes the valuation actually reads — tenure,
journal density, counterparty breadth, win rate, and recency — so the spread of
prices comes out of the data rather than out of a designer's sense of what looks
good on a chart. One is deliberately stale, and one deliberately has too few
resolved outcomes to score, because a marketplace where every listing looks
healthy teaches a buyer nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .redaction import Sensitivity, mark

__all__ = ["Archetype", "CATALOG", "seed_archetype", "archetype_by_slug"]

#: The demo clock. Everything is dated backwards from here so tenure and
#: recency are properties of the data rather than of when the demo is run.
NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)


def _ts(days_ago: int, hour: int = 9) -> str:
    return (NOW - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


@dataclass(frozen=True)
class Archetype:
    """One agent's whole working memory, before it becomes a listing."""

    slug: str
    name: str
    vertical: str
    role: str
    token_id: int
    #: What the seller asks, as a multiple of the agent's own computed
    #: valuation. Expressed as a ratio rather than an absolute price because
    #: the valuation is derived from the memory at export time — hardcoding a
    #: price would let the two drift until the marketplace contradicted itself.
    #: A seller asking above their reference figure is a real marketplace
    #: signal, so the spread is deliberate.
    ask_ratio: str
    counterparties: tuple[tuple[str, str, str, str, str], ...]
    preferences: tuple[tuple[str, dict[str, Any]], ...]
    learned: tuple[tuple[str, str, int, str], ...]
    commitments: tuple[tuple[str, dict[str, Any]], ...]
    working_state: dict[str, Any]
    reference: tuple[str, str]
    journal: tuple[tuple[int, str], ...]        # (days ago, line)
    non_transferable: tuple[str, str, str] | None = None
    public_slugs: tuple[str, ...] = ()
    edges: tuple[tuple[tuple[str, str], tuple[str, str], str], ...] = field(default_factory=tuple)

    @property
    def agent_identity(self) -> str:
        return f"erc8004:84532:{self.token_id:04d}"

    @property
    def listing_id(self) -> str:
        return f"listing-{self.token_id:04d}"

    def asking_price(self, valuation: Decimal) -> int:
        """The asking price in USDC minor units, from a computed valuation."""
        dollars = (valuation * Decimal(self.ask_ratio)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return int(dollars * 1_000_000)

    @property
    def tenant_id(self) -> str:
        return f"tenant-{self.slug}"


CATALOG: tuple[Archetype, ...] = (
    Archetype(
        slug="halcyon-talent",
        name="Halcyon Talent",
        vertical="Recruiting",
        role="Technical sourcing and screening agent",
        token_id=812,
        ask_ratio="1.18",   # asking above: a full pipeline and an exclusivity window
        counterparties=(
            ("verity-systems", "Verity Systems", "Backend, distributed systems", "monthly",
             "Two-stage loop. Rejects anyone without production Go."),
            ("lumen-health", "Lumen Health", "Clinical data engineering", "quarterly",
             "HIPAA screening required before first call. Slow to decide, high close rate."),
            ("northgate-robotics", "Northgate Robotics", "Controls and embedded", "monthly",
             "Wants candidates who have shipped hardware, not just simulated it."),
            ("pale-fire-labs", "Pale Fire Labs", "ML infrastructure", "biweekly",
             "Moves in 48 hours or not at all. Never counters on comp."),
            ("stanton-freight-tech", "Stanton Freight Tech", "Platform", "quarterly",
             "Budget-constrained. Will trade equity for base."),
            ("orchid-financial", "Orchid Financial", "Risk engineering", "monthly",
             "Compliance review adds two weeks. Plan the pipeline around it."),
            ("westmark-energy", "Westmark Energy", "Data platform", "quarterly",
             "Prefers contract-to-hire. Converts about half."),
        ),
        public_slugs=("verity-systems", "pale-fire-labs"),
        non_transferable=(
            "aperture-defense", "Aperture Defense",
            "Cleared-personnel search under an NDA that forbids assignment.",
        ),
        preferences=(
            ("screening-bar", {"min_years": 4, "note": "Below four years the loop pass rate halves and the client stops trusting the shortlist."}),
            ("outreach-window", {"open_local": "07:00", "close_local": "10:30", "note": "Reply rate outside this window is roughly a third."}),
            ("comp-bands", {"note": "Never quote a band before the client has confirmed it in writing. Two placements were lost to a verbal number that moved."}),
            ("pipeline-ratio", {"target": "6 screened per offer", "note": "Below six the client sees the pipeline as thin regardless of quality."}),
        ),
        learned=(
            ("48-hour-rule", "Pale Fire Labs decides within 48 hours or never comes back.", 14,
             "Front-load their shortlist and hold nothing back for a second round."),
            ("compliance-lag", "Orchid Financial's compliance review adds 14 days to every offer.", 9,
             "Start the background check at the onsite, not at the offer."),
            ("hardware-signal", "Northgate rejects candidates whose robotics work was simulation-only.", 11,
             "Screen for a shipped physical product in the first call."),
            ("contract-conversion", "Westmark converts about half of contract-to-hire placements.", 6,
             "Price the contract assuming a 50% conversion, not 100%."),
        ),
        commitments=(
            ("search-VS-2291", {"counterparty": "Verity Systems", "role": "Staff backend engineer",
                                "fee_usd": 38_000, "status": "shortlist-delivered",
                                "note": "Four candidates sent Tuesday. They have until Friday before the exclusivity lapses."}),
            ("search-PFL-2304", {"counterparty": "Pale Fire Labs", "role": "ML platform lead",
                                 "fee_usd": 52_000, "status": "open",
                                 "note": "48-hour window opened this morning. Everything goes out today or not at all."}),
        ),
        working_state={
            "counterparty": "Verity Systems",
            "commitment": "search-VS-2291",
            "last_message_from_counterparty": "Can we get one more backend profile before Friday?",
            "our_position": "Yes — one more by Thursday noon. Exclusivity lapses Friday, so anything after that is non-exclusive and priced accordingly.",
        },
        reference=("skill/candidate-screening",
                   "Screen for shipped production systems, not for years alone. Never quote a comp band the client has not confirmed in writing. Six screened per offer is the floor the client judges the pipeline on."),
        journal=(
            (287, "registered with the ACP service registry"),
            (280, "opened relationship with Verity Systems"),
            (271, "placed staff backend engineer at Verity Systems; accepted"),
            (256, "opened relationship with Lumen Health"),
            (243, "submitted clinical data shortlist to Lumen Health; declined on visa timing"),
            (230, "resubmitted Lumen Health shortlist; accepted"),
            (214, "opened relationship with Pale Fire Labs"),
            (208, "placed ML infrastructure engineer at Pale Fire Labs; accepted"),
            (191, "opened relationship with Northgate Robotics"),
            (183, "Northgate rejected three of four candidates on simulation-only experience"),
            (176, "resubmitted Northgate shortlist screened for shipped hardware; accepted"),
            (160, "opened relationship with Orchid Financial"),
            (149, "Orchid offer stalled 14 days in compliance; candidate withdrew; lost"),
            (138, "opened relationship with Westmark Energy"),
            (129, "placed contract-to-hire data engineer at Westmark; accepted"),
            (114, "opened relationship with Stanton Freight Tech"),
            (103, "Stanton declined on comp; offered equity instead; settled"),
            (88, "placed second backend engineer at Verity Systems; accepted"),
            (71, "Pale Fire Labs search closed inside 48 hours; accepted"),
            (57, "learning pass accepted skill reference/skill/candidate-screening"),
            (44, "placed controls engineer at Northgate Robotics; accepted"),
            (31, "Westmark contract-to-hire converted; accepted"),
            (18, "Lumen Health search opened and filled; accepted"),
            (6, "Verity Systems shortlist delivered; exclusivity runs to Friday"),
            (0, "Pale Fire Labs opened a 48-hour ML platform lead search"),
        ),
        edges=(
            (("commitment", "search-VS-2291"), ("relationship", "verity-systems"), "engaged-on"),
            (("commitment", "search-PFL-2304"), ("relationship", "pale-fire-labs"), "engaged-on"),
            (("learned-behavior", "48-hour-rule"), ("relationship", "pale-fire-labs"), "learned-from"),
            (("learned-behavior", "compliance-lag"), ("relationship", "orchid-financial"), "learned-from"),
            (("learned-behavior", "hardware-signal"), ("relationship", "northgate-robotics"), "learned-from"),
            (("learned-behavior", "contract-conversion"), ("relationship", "westmark-energy"), "learned-from"),
        ),
    ),
    Archetype(
        slug="bright-harbor",
        name="Bright Harbor Retention",
        vertical="Customer success",
        role="Subscription retention and win-back agent",
        token_id=641,
        ask_ratio="1.05",
        counterparties=(
            ("tidewater-media", "Tidewater Media", "Annual, 1,400 seats", "weekly",
             "Churns on invoice friction, not on price. Fix billing first."),
            ("cobalt-studio", "Cobalt Studio", "Monthly, 90 seats", "weekly",
             "Price-sensitive. Accepts a two-month credit over a discount."),
            ("fennel-and-co", "Fennel & Co", "Annual, 300 seats", "monthly",
             "Renews without contact if the usage report lands before the 25th."),
            ("harlow-partners", "Harlow Partners", "Annual, 2,100 seats", "monthly",
             "Escalates to their CFO on any price change. Give 60 days' notice."),
            ("saltmarsh-group", "Saltmarsh Group", "Monthly, 45 seats", "weekly",
             "Two failed win-backs. Third attempt is not worth the contact budget."),
        ),
        public_slugs=("fennel-and-co",),
        preferences=(
            ("discount-ceiling", {"max_pct": 18, "note": "Above 18% the account never returns to list price."}),
            ("contact-cadence", {"note": "Never more than one outreach per fortnight. Two in a week reads as desperation and the reply rate drops."}),
            ("credit-over-discount", {"note": "A service credit preserves the contracted rate; a discount resets the anchor permanently."}),
        ),
        learned=(
            ("invoice-friction", "Tidewater churns on billing problems, never on price.", 12,
             "Route their tickets to billing before offering any commercial concession."),
            ("report-before-25th", "Fennel & Co renews silently if the usage report arrives before the 25th.", 8,
             "Ship it on the 22nd. Do not call."),
            ("cfo-escalation", "Harlow escalates every price change to their CFO.", 5,
             "Give 60 days' notice and pre-brief the account lead."),
        ),
        commitments=(
            ("winback-CS-118", {"counterparty": "Cobalt Studio", "offer": "two-month service credit",
                                "value_usd": 4_200, "status": "open",
                                "note": "Offered Monday. They asked for a week to decide."}),
        ),
        working_state={
            "counterparty": "Cobalt Studio",
            "commitment": "winback-CS-118",
            "last_message_from_counterparty": "Can you do 20% off instead of the credit?",
            "our_position": "No — the ceiling is 18%, and a discount resets the anchor. The two-month credit is worth more to them and preserves the contracted rate.",
        },
        reference=("skill/retention-playbook",
                   "Diagnose before conceding: most churn is friction, not price. Prefer a service credit to a discount. Never exceed an 18% discount, and never contact more than once a fortnight."),
        journal=tuple(
            [(112, "registered with the ACP service registry")]
            + [
                (110 - i * 2, line)
                for i, line in enumerate([
                    "opened relationship with Tidewater Media",
                    "Tidewater renewal at risk on billing errors; routed to billing; accepted",
                    "opened relationship with Fennel & Co",
                    "Fennel & Co usage report sent on the 22nd; renewed; accepted",
                    "opened relationship with Cobalt Studio",
                    "Cobalt Studio requested 25% discount; countered with credit; declined",
                    "Cobalt Studio re-engaged; countered with two-month credit; accepted",
                    "opened relationship with Harlow Partners",
                    "Harlow price change escalated to CFO; 60-day notice given; accepted",
                    "opened relationship with Saltmarsh Group",
                    "Saltmarsh win-back attempt one; declined",
                    "Saltmarsh win-back attempt two; declined",
                    "Tidewater quarterly review; renewed; accepted",
                    "Fennel & Co usage report sent; renewed; accepted",
                    "Harlow seat expansion to 2,100; accepted",
                    "learning pass accepted skill reference/skill/retention-playbook",
                    "Cobalt Studio monthly renewal; accepted",
                    "Tidewater billing escalation resolved; renewed; accepted",
                    "Fennel & Co renewed silently; accepted",
                    "Harlow annual renewal; accepted",
                    "Cobalt Studio churn signal detected; win-back opened",
                ])
            ]
        ),
        edges=(
            (("commitment", "winback-CS-118"), ("relationship", "cobalt-studio"), "offered-to"),
            (("learned-behavior", "invoice-friction"), ("relationship", "tidewater-media"), "learned-from"),
            (("learned-behavior", "report-before-25th"), ("relationship", "fennel-and-co"), "learned-from"),
            (("learned-behavior", "cfo-escalation"), ("relationship", "harlow-partners"), "learned-from"),
        ),
    ),
    Archetype(
        slug="ironvane",
        name="Ironvane Procurement",
        vertical="Procurement",
        role="Industrial component sourcing agent",
        token_id=305,
        ask_ratio="0.95",   # asking under: thin counterparty breadth, and the seller knows it
        counterparties=(
            ("kessler-bearings", "Kessler Bearings", "Precision bearings", "quarterly",
             "Holds price for 90 days if the order is placed before quarter end."),
            ("vantar-alloys", "Vantar Alloys", "Specialty steel", "quarterly",
             "Lead time is the negotiable term, not the price. Never the price."),
            ("dunmore-castings", "Dunmore Castings", "Cast housings", "monthly",
             "Quality escapes cluster after a tooling change. Inspect the first lot."),
        ),
        public_slugs=("kessler-bearings",),
        preferences=(
            ("single-source-limit", {"max_pct_of_spend": 35, "note": "Above 35% with one supplier the negotiating position is gone."}),
            ("quarter-end-timing", {"note": "Place the large orders in the last two weeks of a quarter. Suppliers hold price to make their number."}),
            ("inspection-trigger", {"note": "Inspect the first lot after any supplier tooling change, without exception."}),
        ),
        learned=(
            ("lead-time-lever", "Vantar will move lead time by weeks but never moves price.", 9,
             "Negotiate delivery, not unit cost."),
            ("quarter-end-price-hold", "Kessler holds price 90 days on orders placed before quarter end.", 7,
             "Batch the annual requirement into the last fortnight of Q2."),
        ),
        commitments=(
            ("po-KB-7741", {"counterparty": "Kessler Bearings", "line": "Precision bearings, 12k units",
                            "value_usd": 214_000, "status": "awaiting-countersignature",
                            "note": "Price held to the end of the quarter. Countersignature due in nine days."}),
        ),
        working_state={
            "counterparty": "Kessler Bearings",
            "commitment": "po-KB-7741",
            "last_message_from_counterparty": "Can you confirm the 12k volume before we lock the price?",
            "our_position": "Confirm 12k. The 90-day hold only applies if the PO lands before quarter end, so this needs countersigning within nine days.",
        },
        reference=("skill/supplier-negotiation",
                   "Find each supplier's negotiable term — it is rarely price. Never let one supplier exceed 35% of category spend. Time large orders to quarter end."),
        journal=(
            (203, "registered with the ACP service registry"),
            (196, "opened relationship with Kessler Bearings"),
            (188, "bearings order at list; declined the counter; settled at list with extended terms"),
            (171, "opened relationship with Vantar Alloys"),
            (160, "steel price negotiation refused; renegotiated lead time instead; accepted"),
            (144, "opened relationship with Dunmore Castings"),
            (133, "first lot after tooling change failed inspection; rejected"),
            (126, "Dunmore corrective action accepted; second lot passed; accepted"),
            (109, "quarter-end bearings order placed; price held 90 days; accepted"),
            (92, "learning pass accepted skill reference/skill/supplier-negotiation"),
            (78, "Vantar lead time reduced by three weeks; accepted"),
            (61, "Dunmore housing order; accepted"),
            (40, "annual bearings requirement batched to quarter end; accepted"),
            (21, "Vantar steel order; accepted"),
            (9, "PO KB-7741 issued; awaiting countersignature"),
        ),
        edges=(
            (("commitment", "po-KB-7741"), ("relationship", "kessler-bearings"), "ordered-from"),
            (("learned-behavior", "lead-time-lever"), ("relationship", "vantar-alloys"), "learned-from"),
            (("learned-behavior", "quarter-end-price-hold"), ("relationship", "kessler-bearings"), "learned-from"),
        ),
    ),
    Archetype(
        slug="cedar-vale",
        name="Cedar & Vale",
        vertical="Property",
        role="Residential leasing and renewal agent",
        token_id=1174,
        ask_ratio="0.88",   # stale, and priced to move
        counterparties=(
            ("marlow-court", "Marlow Court", "42 units", "annual",
             "Renewals cluster in August. Start outreach in June or lose the month."),
            ("selby-row", "Selby Row", "18 units", "annual",
             "Owner refuses concessions. Vacancy is cheaper to them than a rent reduction."),
            ("thornfield-mews", "Thornfield Mews", "26 units", "annual",
             "Accepts one month free over a rent cut. Same cost, better optics on the rent roll."),
        ),
        public_slugs=(),
        preferences=(
            ("renewal-lead-time", {"days": 75, "note": "Below 75 days the renewal rate drops by about a fifth."}),
            ("concession-form", {"note": "One month free beats a rent reduction: identical cost, and the headline rent on the roll is unchanged."}),
        ),
        learned=(
            ("august-cluster", "Marlow Court renewals cluster in August.", 6,
             "Begin outreach in the first week of June."),
            ("vacancy-over-discount", "Selby Row's owner prefers a vacant unit to a reduced rent.", 4,
             "Do not propose reductions. Propose term length instead."),
        ),
        commitments=(
            ("renewal-MC-2026", {"counterparty": "Marlow Court", "units": 11,
                                 "status": "open", "note": "Eleven August renewals outstanding. Outreach started late this year."}),
        ),
        working_state={
            "counterparty": "Marlow Court",
            "commitment": "renewal-MC-2026",
            "last_message_from_counterparty": "How many of the eleven have signed?",
            "our_position": "Four signed. Outreach started in July rather than June, which historically costs about a fifth of the renewals.",
        },
        reference=("skill/renewal-outreach",
                   "Start renewal outreach 75 days out. Offer a free month rather than a rent reduction — the cost is identical and the rent roll is unaffected."),
        journal=(
            (421, "registered with the ACP service registry"),
            (410, "opened relationship with Marlow Court"),
            (398, "August renewal cycle; 34 of 42 renewed; accepted"),
            (377, "opened relationship with Selby Row"),
            (362, "proposed rent reduction at Selby Row; refused by owner; declined"),
            (349, "Selby Row term-length proposal; accepted"),
            (330, "opened relationship with Thornfield Mews"),
            (318, "Thornfield renewals with one month free; accepted"),
            (296, "Marlow Court mid-year vacancies filled; accepted"),
            (274, "learning pass accepted skill reference/skill/renewal-outreach"),
            (251, "Thornfield annual renewal cycle; accepted"),
            (229, "Selby Row renewals at list rent; accepted"),
            (198, "Marlow Court August cycle; 38 of 42 renewed; accepted"),
            (147, "Thornfield renewal cycle; accepted"),
            (96, "Marlow Court outreach opened late; eleven outstanding"),
        ),
        edges=(
            (("commitment", "renewal-MC-2026"), ("relationship", "marlow-court"), "renewing"),
            (("learned-behavior", "august-cluster"), ("relationship", "marlow-court"), "learned-from"),
            (("learned-behavior", "vacancy-over-discount"), ("relationship", "selby-row"), "learned-from"),
        ),
    ),
    Archetype(
        slug="quantile-research",
        name="Quantile Research",
        vertical="Research",
        role="Competitive intelligence and pricing research agent",
        token_id=2098,
        ask_ratio="1.10",
        counterparties=(
            ("aldervale-capital", "Aldervale Capital", "Sector pricing briefs", "monthly",
             "Wants the methodology appendix or the brief is not read."),
            ("kestrel-consumer", "Kestrel Consumer", "Shelf-price tracking", "weekly",
             "Cares about the delta, not the level. Lead with what moved."),
        ),
        public_slugs=("aldervale-capital",),
        preferences=(
            ("methodology-appendix", {"note": "Always attach the method. Aldervale discards briefs without it."}),
            ("delta-first", {"note": "Lead with what changed since the last brief, never with the absolute level."}),
        ),
        learned=(
            ("appendix-requirement", "Aldervale discards any brief without a methodology appendix.", 5,
             "Attach it before sending, every time."),
            ("delta-framing", "Kestrel reads only the change section.", 4,
             "Put the delta in the first paragraph and the levels in a table."),
        ),
        commitments=(
            ("brief-AC-Q3", {"counterparty": "Aldervale Capital", "deliverable": "Q3 sector pricing brief",
                             "fee_usd": 18_500, "status": "open",
                             "note": "Due in four days. Methodology appendix outstanding."}),
        ),
        working_state={
            "counterparty": "Aldervale Capital",
            "commitment": "brief-AC-Q3",
            "last_message_from_counterparty": "Is the Q3 brief still landing Friday?",
            "our_position": "Yes. The appendix is the outstanding piece, and it goes with the brief — they discard anything sent without it.",
        },
        reference=("skill/brief-construction",
                   "Lead with the delta, never the level. Attach the methodology appendix without exception. Levels belong in a table, not in prose."),
        journal=(
            (64, "registered with the ACP service registry"),
            (58, "opened relationship with Aldervale Capital"),
            (51, "Q1 pricing brief delivered without appendix; rejected"),
            (47, "Q1 brief resubmitted with appendix; accepted"),
            (39, "opened relationship with Kestrel Consumer"),
            (33, "first shelf-price brief led with levels; poor engagement; declined"),
            (28, "shelf-price brief restructured delta-first; accepted"),
            (19, "learning pass accepted skill reference/skill/brief-construction"),
            (11, "Q2 sector brief delivered; accepted"),
            (4, "Q3 brief opened; appendix outstanding"),
        ),
        edges=(
            (("commitment", "brief-AC-Q3"), ("relationship", "aldervale-capital"), "deliverable-for"),
            (("learned-behavior", "appendix-requirement"), ("relationship", "aldervale-capital"), "learned-from"),
            (("learned-behavior", "delta-framing"), ("relationship", "kestrel-consumer"), "learned-from"),
        ),
    ),
)


def archetype_by_slug(slug: str) -> Archetype:
    for a in CATALOG:
        if a.slug == slug:
            return a
    raise KeyError(f"no archetype {slug!r}")


def seed_archetype(sink: Any, archetype: Archetype) -> dict[str, int]:
    """Write one archetype into a tenant. Returns per-tier counts."""
    client = sink.client
    counts = dict.fromkeys(("entity", "event", "state", "reference", "relation"), 0)

    client.set_entity(
        "identity",
        archetype.agent_identity,
        mark(
            {
                "name": archetype.name,
                "role": archetype.role,
                "vertical": archetype.vertical,
                "erc8004": archetype.agent_identity,
            },
            sensitivity=Sensitivity.PUBLIC,
        ),
    )
    counts["entity"] += 1

    for slug, company, focus, cadence, note in archetype.counterparties:
        client.set_entity(
            "relationship",
            slug,
            mark(
                {"company": company, "focus": focus, "cadence": cadence, "note": note},
                sensitivity=(
                    Sensitivity.PUBLIC
                    if slug in archetype.public_slugs
                    else Sensitivity.PRIVATE
                ),
            ),
            status="active",
        )
        counts["entity"] += 1

    if archetype.non_transferable:
        slug, company, note = archetype.non_transferable
        client.set_entity(
            "relationship",
            slug,
            mark(
                {"company": company, "focus": "withheld", "note": note},
                sensitivity=Sensitivity.PRIVATE,
                transferable=False,
            ),
            status="active",
        )
        counts["entity"] += 1

    for name, body in archetype.preferences:
        client.set_entity("preference", name, mark(body, sensitivity=Sensitivity.PRIVATE))
        counts["entity"] += 1

    for name, pattern, observed, action in archetype.learned:
        client.set_entity(
            "learned-behavior",
            name,
            mark(
                {"pattern": pattern, "observed_count": observed, "action": action},
                sensitivity=Sensitivity.PRIVATE,
            ),
        )
        counts["entity"] += 1

    for name, body in archetype.commitments:
        client.set_entity(
            "commitment", name, mark(body, sensitivity=Sensitivity.PRIVATE), status="open"
        )
        counts["entity"] += 1

    client.set_state("current-negotiation", archetype.working_state)
    counts["state"] += 1

    key, text = archetype.reference
    client.set_reference(key, text, metadata={"source": "learning-pass"})
    counts["reference"] += 1

    for days_ago, line in archetype.journal:
        client.write_event(acted=[line], ts=_ts(days_ago))
        counts["event"] += 1

    counts["relation"] += _write_edges(client, list(archetype.edges))
    return counts


def _write_edges(client: Any, edges: list[Any]) -> int:
    """Write entity_relations rows. The client exposes no public edge API."""
    import uuid

    tenant = client.get_tenant()
    written = 0
    with client.storage.transaction() as conn:
        for (f_cat, f_name), (t_cat, t_name), relation in edges:
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
                (uuid.uuid4().hex, tenant, f["id"], t["id"], relation),
            )
            written += 1
    return written
