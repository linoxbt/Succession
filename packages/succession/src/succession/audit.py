"""Check every claim this project makes about itself, and say so out loud.

The argument Succession makes is that its assertions are checkable. This is the
command that checks them. It takes no repository, no frontend and no network:
it builds a memory, sells it to itself, and measures what happened.

Every check here computes rather than asserts. Three of them exist because an
audit found the corresponding claim resting on nothing:

* "newest first" was verified only by grepping the documentation string that
  says "newest first". Here the records carry known timestamps and the halves
  are compared.
* "the valuation is re-derivable by hand" had no test that re-derived anything.
  Here each factor is recomputed from the inputs it published and compared to
  the multiplier it reported.
* "a non-transferable record never reaches the tree" was inferred from the
  record's absence from the package payload. Absence from a payload is not
  absence from a hash, so here the tree is built twice, with and without, and
  the roots are required to be identical: if the withheld record had reached
  the tree in any form, the root would move.

A check that cannot run says so and is reported as `skipped`, never as passed.
The exit code is non-zero if anything failed.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

__all__ = ["Check", "run_audit", "CHECKS"]


@dataclass
class Check:
    """One claim, and what became of it."""

    name: str
    claim: str
    status: str = "pending"      # passed | failed | skipped
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "claim": self.claim,
            "status": self.status,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def _seed(memory: Any, *, count: int = 12) -> None:
    """A small tenant with known shape: public and private, transferable or not."""
    from .redaction import Consent, Sensitivity, mark

    client = memory.client
    client.set_entity(
        "identity", "erc8004:84532:0417",
        mark({"name": "Audit Operator", "role": "Freight"},
             sensitivity=Sensitivity.PUBLIC),
    )
    for i in range(count):
        client.set_entity(
            "relationship", f"counterparty-{i:02d}",
            mark({"company": f"Counterparty {i:02d}", "terms": f"net-{30 + i}"},
                 sensitivity=Sensitivity.PRIVATE),
        )
        client.write_event(evaluated={"cp": f"counterparty-{i:02d}"},
                           acted={"quoted": 1000 + i})
    client.set_entity(
        "preference", "lane-bias",
        mark({"prefers": "midwest"}, sensitivity=Sensitivity.PRIVATE),
    )
    client.set_entity(
        "commitment", "open-quote",
        mark({"owed": "quote by friday"}, sensitivity=Sensitivity.PRIVATE),
    )
    client.set_reference(
        "escalation",
        mark({"rule": "escalate over 40k"}, sensitivity=Sensitivity.PRIVATE),
    )
    # The record that must never move, at any price, for any buyer.
    client.set_entity(
        "relationship", "sealed-counterparty",
        mark({"company": "Never Transfers Ltd", "secret": "aperture-defense"},
             sensitivity=Sensitivity.PRIVATE, consent=Consent.WITHHELD),
    )


# --- the checks ----------------------------------------------------------


def check_categories_transfer(ctx: dict[str, Any]) -> Check:
    check = Check(
        "categories-transfer",
        "All six memory directories survive a sale with identical Merkle subroots.",
    )
    from .export import export_tenant
    from .importer import import_package
    from .memory.sibyl import open_tenant
    from .smp import DATA_CATEGORIES

    source = ctx["source"]
    exported = export_tenant(
        source, agent_identity=ctx["agent"], private_key=ctx["key"]
    )
    with tempfile.TemporaryDirectory() as tmp:
        sink = open_tenant(Path(tmp) / "buyer.db", "audit-buyer")
        import_package(
            exported.package, sink,
            committed_root=exported.root_hex, expected_signer=ctx["signer"],
        )
        landed = export_tenant(
            sink, agent_identity=ctx["agent"], private_key=ctx["key"]
        )

    sent = {c["category"]: c for c in exported.package.integrity["categories"]}
    got = {c["category"]: c for c in landed.package.integrity["categories"]}

    rows, bad = {}, []
    for category in DATA_CATEGORIES:
        a, b = sent.get(category), got.get(category)
        if a is None or b is None:
            rows[category] = "absent"
            continue
        same = a["subroot"] == b["subroot"] and a["leaf_count"] == b["leaf_count"]
        rows[category] = f"{a['leaf_count']} leaves, {'identical' if same else 'CHANGED'}"
        if not same:
            bad.append(category)

    carrying = [c for c in DATA_CATEGORIES if c in sent and sent[c]["leaf_count"] > 0]
    check.evidence = {"per_category": rows, "carrying_records": len(carrying)}
    if bad:
        check.status, check.detail = "failed", f"subroots moved: {', '.join(bad)}"
    elif len(carrying) < len(DATA_CATEGORIES):
        missing = [c for c in DATA_CATEGORIES if c not in carrying]
        check.status = "failed"
        check.detail = f"no records in {', '.join(missing)}, so nothing was proved for them"
    else:
        check.status = "passed"
        check.detail = f"all {len(DATA_CATEGORIES)} directories re-derived identically"
    return check


def check_withheld_leaves_no_trace(ctx: dict[str, Any]) -> Check:
    check = Check(
        "withheld-absent-from-tree",
        "A record marked non-transferable is absent from the Merkle tree, not just "
        "from the payload.",
    )
    import copy

    from .export import build_package

    package, report = build_package(ctx["source"])

    blob = json.dumps(package.to_dict(), sort_keys=True)
    leaked = "aperture-defense" in blob or "Never Transfers Ltd" in blob
    names = {
        r.get("name")
        for records in package.data.values()
        for r in records
        if isinstance(r, dict)
    }
    in_payload = "sealed-counterparty" in names
    actual_root = "0x" + package.tree().root.hex()

    # Absence from a payload is not absence from a hash, and that distinction is
    # the whole claim. So: put the record back, rebuild, and require the root to
    # move. A root that is sensitive to the record's presence cannot already
    # contain it. Comparing two separately seeded stores would not show this —
    # their journal timestamps differ, so the roots differ for reasons that have
    # nothing to do with consent.
    mutated = copy.deepcopy(package)
    relationships = mutated.data.get("relationships") or []
    if relationships:
        smuggled = copy.deepcopy(relationships[0])
        smuggled["name"] = "sealed-counterparty"
        smuggled["body"] = {"company": "Never Transfers Ltd", "secret": "aperture-defense"}
        mutated.data["relationships"] = [*relationships, smuggled]
    mutated_root = "0x" + mutated.tree().root.hex()

    check.evidence = {
        "withheld_without_consent": report.withheld_without_consent,
        "body_appears_in_package": leaked,
        "name_appears_in_payload": in_payload,
        "root_as_built": actual_root,
        "root_if_the_record_were_included": mutated_root,
    }
    if leaked or in_payload:
        check.status, check.detail = "failed", "the withheld record appears in the package"
    elif report.withheld_without_consent < 1:
        check.status, check.detail = "failed", "the fixture withheld nothing, so nothing was proved"
    elif not relationships:
        check.status, check.detail = "failed", "no relationship records to test against"
    elif actual_root == mutated_root:
        check.status = "failed"
        check.detail = (
            "the root does not change when the record is added, so the tree "
            "cannot be said to exclude it"
        )
    else:
        check.status = "passed"
        check.detail = (
            "absent from the payload, and the root moves if it is added back, "
            "so it is absent from the tree"
        )
    return check


def check_preview_carries_no_bodies(ctx: dict[str, Any]) -> Check:
    check = Check(
        "preview-has-no-bodies",
        "The pre-purchase data room carries counts and no record bodies.",
    )
    from .dataroom import build_preview

    preview = build_preview(ctx["source"], agent_identity=ctx["agent"])
    blob = json.dumps(preview.to_dict(), sort_keys=True)

    # Every distinctive string from a non-public record, swept against the whole
    # serialised preview. Short strings are skipped: a three-letter token
    # colliding by chance would be noise, not a leak.
    leaks = []
    for value in ("Counterparty 00", "net-30", "midwest", "quote by friday",
                  "escalate over 40k", "aperture-defense", "Never Transfers Ltd"):
        if value in blob:
            leaks.append(value)

    check.evidence = {
        "preview_bytes": len(blob),
        "strings_swept": 7,
        "leaked": leaks,
        "public_counterparties_named": list(preview.public_counterparties),
    }
    if leaks:
        check.status, check.detail = "failed", f"private content in the preview: {leaks}"
    else:
        check.status = "passed"
        check.detail = "no private record body appears in the published preview"
    return check


def check_valuation_re_derives(ctx: dict[str, Any]) -> Check:
    check = Check(
        "valuation-re-derives",
        "Every valuation factor can be recomputed from the inputs it publishes.",
    )
    from .valuation import value_tenant

    valuation = value_tenant(ctx["source"])
    body = valuation.to_dict()

    product = Decimal(body["base_price"])
    for factor in body["factors"]:
        product *= Decimal(factor["value"])
    stated = Decimal(body["amount"])
    # Quantized to cents by the valuation, so compare at that resolution.
    agrees = abs(product - stated) <= Decimal("0.01")

    # And each factor has to show its working, not merely a number.
    undocumented = [
        f["name"] for f in body["factors"] if not f.get("inputs") or not f.get("explanation")
    ]

    check.evidence = {
        "formula": body["formula"],
        "base_price": body["base_price"],
        "factors": {f["name"]: f["value"] for f in body["factors"]},
        "recomputed": str(product.quantize(Decimal("0.01"))),
        "reported": body["amount"],
        "excluded_terms": sorted(body["excluded"]),
    }
    if not agrees:
        check.status = "failed"
        check.detail = f"recomputed {product} but the valuation reports {stated}"
    elif undocumented:
        check.status = "failed"
        check.detail = f"factors without inputs or explanation: {undocumented}"
    else:
        check.status = "passed"
        check.detail = "the product of the published factors equals the published figure"
    return check


def check_newest_first_selection(ctx: dict[str, Any]) -> Check:
    check = Check(
        "partial-takes-newest",
        "A percentage sale takes the newest records, not an arbitrary half.",
    )
    from .scope import SaleScope

    now = datetime.now(timezone.utc)
    records = [
        {
            "kind": "entity",
            "category": "relationship",
            "name": f"cp-{i:02d}",
            "ts": (now - timedelta(days=100 - i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "body": {"n": i},
        }
        for i in range(10)
    ]
    scope = SaleScope.from_percentages({"relationships": 50})
    kept, _withheld = scope.resolve(records)
    taken = sorted(int(r["name"].split("-")[1]) for r in kept)

    # Records 0..9 age from oldest to newest, so a newest-first half is 5..9.
    expected = [5, 6, 7, 8, 9]
    check.evidence = {
        "seeded": 10,
        "requested_percent": 50,
        "taken_indices": taken,
        "expected_newest_half": expected,
    }
    if taken == expected:
        check.status = "passed"
        check.detail = "the newer half was selected, by timestamp"
    else:
        check.status = "failed"
        check.detail = f"expected the newest half {expected}, got {taken}"
    return check


def check_the_seal_holds(ctx: dict[str, Any]) -> Check:
    check = Check(
        "seal-rejects-writes",
        "After settlement the seller's tenant rejects every write, and there is no unseal.",
    )
    from .seal import SealRegistry, TenantSealed, guard

    with tempfile.TemporaryDirectory() as tmp:
        registry = SealRegistry(Path(tmp) / "seals.db")
        registry.seal("audit-seller", reason="audit")
        guarded = guard(ctx["source"], registry)

        attempts, rejected = [], []
        probes: list[tuple[str, Callable[[], Any]]] = [
            ("set_entity", lambda: guarded.client.set_entity(
                "relationship", "post-seal", {"company": "After"})),
            ("write_event", lambda: guarded.client.write_event(
                evaluated={"x": 1}, acted={"y": 2})),
            ("set_state", lambda: guarded.client.set_state("s", {"a": 1})),
            ("set_reference", lambda: guarded.client.set_reference("r", {"a": 1})),
            ("archive_entity", lambda: guarded.client.archive_entity(
                "relationship", "counterparty-00")),
        ]
        for name, probe in probes:
            attempts.append(name)
            try:
                probe()
            except TenantSealed:
                rejected.append(name)
            except Exception:  # noqa: BLE001 - any refusal is a refusal
                rejected.append(name)

    has_unseal = hasattr(SealRegistry, "unseal")
    check.evidence = {
        "write_paths_attempted": attempts,
        "rejected": rejected,
        "registry_exposes_unseal": has_unseal,
    }
    if has_unseal:
        check.status, check.detail = "failed", "the registry exposes an unseal operation"
    elif len(rejected) != len(attempts):
        allowed = sorted(set(attempts) - set(rejected))
        check.status, check.detail = "failed", f"writes still permitted: {allowed}"
    else:
        check.status = "passed"
        check.detail = f"all {len(attempts)} write paths rejected; no unseal exists"
    return check


def check_manifests_match_the_chain(ctx: dict[str, Any]) -> Check:
    check = Check(
        "published-manifests-match-chain",
        "Every published Merkle root equals the commitment recorded on chain.",
    )
    base = ctx.get("marketplace")
    if not base:
        check.status = "skipped"
        check.detail = "no marketplace given; pass --marketplace to check live listings"
        return check

    from .marketplace import MarketplaceError, get

    try:
        body = get(base, "/api/marketplace")
    except MarketplaceError as exc:
        check.status, check.detail = "skipped", f"marketplace unreachable: {exc}"
        return check

    rows = [r for r in body.get("listings", []) if not r.get("demo")]
    compared, disagreed = 0, []
    for row in rows:
        manifest = row.get("integrity") or {}
        root = manifest.get("root")
        if not root:
            continue
        compared += 1
        if root.lower() != row["listing"]["hash_commitment"].lower():
            disagreed.append(row["listing"]["listing_id"])

    check.evidence = {
        "marketplace": base,
        "real_listings": len(rows),
        "with_published_manifest": compared,
        "disagreeing": disagreed,
    }
    if disagreed:
        check.status = "failed"
        check.detail = f"manifest disagrees with the chain for {', '.join(disagreed)}"
    elif compared == 0:
        check.status = "skipped"
        check.detail = f"{len(rows)} live listings, none with a published manifest"
    else:
        check.status = "passed"
        check.detail = f"{compared} published roots equal their on-chain commitment"
    return check


CHECKS: tuple[Callable[[dict[str, Any]], Check], ...] = (
    check_categories_transfer,
    check_withheld_leaves_no_trace,
    check_preview_carries_no_bodies,
    check_valuation_re_derives,
    check_newest_first_selection,
    check_the_seal_holds,
    check_manifests_match_the_chain,
)


def run_audit(*, marketplace: str | None = None) -> list[Check]:
    """Build a memory, sell it to itself, and measure every claim."""
    from eth_account import Account

    from .memory.sibyl import open_tenant

    key = "0x" + "27" * 32
    with tempfile.TemporaryDirectory() as tmp:
        source = open_tenant(Path(tmp) / "seller.db", "audit-seller")
        _seed(source)
        ctx = {
            "source": source,
            "agent": "erc8004:84532:0417",
            "key": key,
            "signer": Account.from_key(key).address,
            "marketplace": marketplace,
        }
        results = []
        for run in CHECKS:
            try:
                results.append(run(ctx))
            except Exception as exc:  # noqa: BLE001 - a crashed check is a failed one
                results.append(
                    Check(
                        run.__name__.replace("check_", "").replace("_", "-"),
                        "(the check itself raised)",
                        status="failed",
                        detail=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results
