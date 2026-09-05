"""Selling part of a memory, reproducibly.

A percentage is only meaningful if it resolves to the same records every time:
the buyer re-hashes what lands in their store against a root committed before
they existed, so a selection rule that drifted between runs would break
verification rather than merely annoy someone.

The regression this file exists to prevent is subtler than that, and it was
real. `relationships/` holds two different kinds of thing — counterparty
entities, and the WARM edges between them. Treating them as one pool and taking
a percentage across both selected mostly edges, whose endpoints had not been
selected, and the dangling-edge prune then correctly discarded them. "50% of
relationships" produced *zero* relationship records while the listing claimed
half. Edges now follow their endpoints instead of competing with them.
"""

from __future__ import annotations

import pytest

from succession.demokeys import SELLER
from succession.export import export_tenant
from succession.redaction import Consent, Sensitivity, mark, read_disclosure
from succession.scope import (
    CategorySelection,
    SaleScope,
    record_fingerprint,
    take_inventory,
)


# --- inventory -----------------------------------------------------------


def test_inventory_reports_every_category(seller):
    inventory = take_inventory(seller)
    assert set(inventory) >= {
        "identity",
        "relationships",
        "preferences",
        "history",
        "commitments",
        "learned-behaviors",
    }
    for entry in inventory.values():
        assert entry.total == (
            entry.sellable + entry.withheld_by_seller + entry.withheld_without_consent
        )


def test_depth_bands_describe_what_is_there(seller):
    inventory = take_inventory(seller)
    assert inventory["history"].depth == "deep"
    assert inventory["identity"].depth == "thin"
    for entry in inventory.values():
        assert entry.offerable == (entry.sellable > 0)


def test_an_empty_category_is_not_offerable(buyer):
    """A category with nothing in it must not be selectable.

    Offering it produces a listing whose directory exports empty, which is a
    promise the package cannot keep.
    """
    inventory = take_inventory(buyer)
    for entry in inventory.values():
        assert entry.sellable == 0
        assert entry.offerable is False
        assert entry.depth == "empty"


def test_inventory_separates_the_two_reasons_a_record_is_withheld(seller):
    """A seller's own redaction and a counterparty's refusal are different facts."""
    seller.client.set_entity(
        "relationship", "no-consent-here", mark({"c": 1}, consent=Consent.WITHHELD)
    )
    inventory = take_inventory(seller)
    assert inventory["relationships"].withheld_without_consent >= 1


# --- determinism ---------------------------------------------------------


def test_the_same_scope_resolves_identically_every_time(seller):
    """The property everything else depends on."""
    scope = SaleScope.from_percentages({"relationships": 50, "history": 40})
    first = export_tenant(
        seller, agent_identity="a", private_key=SELLER.private_key, scope=scope
    )
    second = export_tenant(
        seller, agent_identity="a", private_key=SELLER.private_key, scope=scope
    )
    assert first.root_hex == second.root_hex


def test_ties_break_on_content_not_row_id(seller):
    """Row ids do not survive a transfer, so ordering cannot depend on them."""
    record = {"kind": "entity", "category": "relationship", "name": "x", "body": {"a": 1}}
    with_id = {**record, "id": "row-999"}
    assert record_fingerprint(record) == record_fingerprint(with_id)


# --- percentages ---------------------------------------------------------


def test_a_larger_percentage_never_yields_fewer_records(seller):
    counts = []
    for percent in (25, 50, 75, 100):
        export = export_tenant(
            seller,
            agent_identity="a",
            private_key=SELLER.private_key,
            scope=SaleScope.from_percentages({"history": percent}),
        )
        counts.append(len(export.package.data.get("history", [])))
    assert counts == sorted(counts), counts
    assert counts[-1] > counts[0]


def test_a_small_percentage_of_a_real_category_is_not_nothing(seller):
    """Rounded up, so 1% of something means "a little", never "none"."""
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"history": 1}),
    )
    assert len(export.package.data.get("history", [])) >= 1


def test_a_category_left_out_of_the_scope_is_not_sold(seller):
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"history": 100}),
    )
    assert not export.package.data.get("preferences")
    assert not export.package.data.get("commitments")


def test_percent_must_be_a_percentage():
    with pytest.raises(ValueError, match="0-100"):
        CategorySelection("history", 140)


# --- the regression this file is named for -------------------------------


def test_selling_half_the_relationships_yields_relationship_records(seller):
    """The bug: edges counted in the percentage, then pruned, leaving nothing."""
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"relationships": 50}),
    )
    assert len(export.package.data.get("relationships", [])) > 0


def test_edges_follow_their_endpoints_rather_than_the_percentage(seller):
    """Widening the scope brings edges back, because their far ends arrive."""
    narrow = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"relationships": 100}),
    )
    wide = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages(
            {"relationships": 100, "learned-behaviors": 100}
        ),
    )
    assert len(wide.package.data["relationships"]) > len(
        narrow.package.data["relationships"]
    )
    assert wide.redaction.withheld_dangling_relations < (
        narrow.redaction.withheld_dangling_relations
    )


# --- the scope is part of what was agreed --------------------------------


def test_the_package_records_the_scope_it_was_built_with(seller):
    """The header binds the permissions document by hash, so this is attested."""
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"history": 60}),
    )
    scope = export.package.permissions["scope"]
    assert scope["selections"] == [{"category": "history", "percent": 60}]
    assert "newest first" in scope["rule"]


def test_a_percentage_applies_to_what_was_sellable_not_the_raw_store(seller):
    """100% of a category never includes what the seller withheld."""
    seller.client.set_entity(
        "preference", "private-one", mark({"x": 1}, transferable=False)
    )
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope.from_percentages({"preferences": 100}),
    )
    for record in export.package.data.get("preferences", []):
        assert read_disclosure(record.get("body")).may_transfer


# --- explicit picks ------------------------------------------------------


def test_naming_records_overrides_the_percentage(seller):
    from succession.export import read_all
    from succession.smp import route

    chosen = [
        record_fingerprint(r)
        for r in read_all(seller)
        if route(r) == "preferences"
    ][:2]
    export = export_tenant(
        seller,
        agent_identity="a",
        private_key=SELLER.private_key,
        scope=SaleScope((CategorySelection("preferences", 100, tuple(chosen)),)),
    )
    assert len(export.package.data.get("preferences", [])) == len(chosen)
