"""The vision, asserted: all six memory categories actually change hands.

Succession's claim is that an agent's accumulated context becomes property.
That claim is only as good as its weakest category. A build where
`learned-behaviors` quietly exports empty, or where `commitments` round-trips
with a different subroot, still passes a whole-package roundtrip test because
the root is computed over whatever was actually there.

So this file checks each category on its own, and it is deliberately written to
fail loudly rather than skip:

* every category in `DATA_CATEGORIES` must carry at least one record
* each must land in the buyer's store with the same leaf count
* each must re-derive an identical subroot from the buyer's own re-export
* adding a seventh category without seeding it must break this file

The last one matters most. The set is the product's promise, so widening the
promise without evidence behind it should not be quiet.
"""

from __future__ import annotations

import pytest

from succession.demokeys import SELLER
from succession.export import export_tenant
from succession.importer import import_package
from succession.smp import DATA_CATEGORIES


def subroots(package) -> dict[str, tuple[str, int]]:
    """`{category: (subroot, leaf_count)}` from the integrity proof."""
    return {
        entry["category"]: (entry["subroot"], entry["leaf_count"])
        for entry in (package.integrity or {}).get("categories", [])
    }


@pytest.fixture
def transferred(seller, buyer, agent_id):
    """A complete sale: export, import into a separate store, re-export."""
    export = export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key
    )
    result = import_package(
        export.package,
        buyer,
        committed_root=export.root_hex,
        expected_signer=SELLER.address,
    )
    # The buyer re-exports their *own* store. Comparing against this rather than
    # against the bytes received is the whole point: it proves the importer
    # wrote what it was given and the engine coerced nothing on the way in.
    reexport = export_tenant(
        buyer, agent_identity=agent_id, private_key=SELLER.private_key
    )
    return export, result, reexport


def test_every_category_carries_something(transferred):
    """A category that exports empty is a promise the product is not keeping."""
    export, _, _ = transferred
    empty = [c for c in DATA_CATEGORIES if not export.package.data.get(c)]
    assert not empty, (
        f"these categories exported no records: {empty}. Each one is part of "
        "what Succession claims transfers, so an empty one is a broken claim "
        "rather than a thin fixture."
    )


def test_every_category_lands_with_the_same_leaf_count(transferred):
    export, _, reexport = transferred
    sent, landed = subroots(export.package), subroots(reexport.package)
    for category in DATA_CATEGORIES:
        assert category in sent, f"{category} has no subroot in the export"
        assert category in landed, f"{category} did not land in the buyer's store"
        assert sent[category][1] == landed[category][1], (
            f"{category}: {sent[category][1]} leaves sent, "
            f"{landed[category][1]} landed"
        )


def test_every_category_re_derives_an_identical_subroot(transferred):
    """Per category, not just in aggregate.

    The whole-package root can match while an individual category is wrong only
    if two categories compensate for each other, which the two-level tree makes
    impossible — but checking per category is what turns that from an argument
    into a test.
    """
    export, _, reexport = transferred
    sent, landed = subroots(export.package), subroots(reexport.package)
    mismatched = [c for c in DATA_CATEGORIES if sent.get(c) != landed.get(c)]
    assert not mismatched, f"subroot changed in transit for: {mismatched}"


def test_the_whole_package_verifies(transferred):
    _, result, _ = transferred
    assert result.verified is True


def test_the_promise_is_exactly_six_categories():
    """A guard on the set itself.

    If someone adds a seventh category, this fails and they have to come here,
    seed it, and prove it transfers before the product starts claiming it does.
    """
    assert set(DATA_CATEGORIES) == {
        "identity",
        "relationships",
        "preferences",
        "history",
        "commitments",
        "learned-behaviors",
    }


def test_a_partial_sale_still_transfers_each_selected_category_whole(
    seller, buyer, agent_id
):
    """Selling a subset must not degrade what is inside the subset."""
    chosen = ["relationships", "commitments"]
    export = export_tenant(
        seller,
        agent_identity=agent_id,
        private_key=SELLER.private_key,
        categories=chosen,
    )
    import_package(
        export.package,
        buyer,
        committed_root=export.root_hex,
        expected_signer=SELLER.address,
    )
    reexport = export_tenant(
        buyer,
        agent_identity=agent_id,
        private_key=SELLER.private_key,
        categories=chosen,
    )
    sent, landed = subroots(export.package), subroots(reexport.package)
    for category in chosen:
        assert sent[category] == landed[category], f"{category} changed in a partial sale"
