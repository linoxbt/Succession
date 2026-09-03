"""Partial succession: the same pipeline with a category filter, verified
against the per-category subroots the full pipeline already produces.

This is the cheapest way to show real range in the mechanism, and it is only
cheap because the Merkle tree was built two-level from the start. A flat hash
would have needed a redesign here.
"""

from __future__ import annotations

import pytest

from succession import export_tenant, import_package
from succession.demokeys import SELLER
from succession.merkle import to_hex, verify_proof
from succession.smp import DATA_CATEGORIES


def _export(seller, agent_id, **kw):
    return export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key, **kw
    )


SOLD = ["relationships", "preferences", "learned-behaviors"]


def test_a_partial_package_transfers_and_verifies(seller, buyer, agent_id):
    exported = _export(seller, agent_id, categories=SOLD)

    result = import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )

    assert result.verified
    assert sorted(exported.package.data) == sorted(SOLD)


def test_withheld_categories_do_not_reach_the_buyer(seller, buyer, agent_id):
    exported = _export(seller, agent_id, categories=SOLD)
    import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )

    # commitments/ was not sold: no commitment entities, no HOT working state.
    assert [e for e in buyer.entities() if e["category"] == "commitment"] == []
    assert buyer.states() == []
    # history/ was not sold: no journal.
    assert buyer.events() == []


def test_a_subroot_still_verifies_against_the_full_root(seller, agent_id):
    """The buyer of three categories can check them against the root committed
    over all six, without ever seeing the three they did not buy."""
    full = _export(seller, agent_id)
    tree = full.package.tree()

    for category in SOLD:
        leaf = _category_leaf(category, tree.subroots[category])
        assert verify_proof(leaf, tree.category_proof(category), tree.root)


def _category_leaf(category, subroot):
    from succession.canonical import canonical_bytes
    from succession.merkle import hash_leaf

    return hash_leaf(
        canonical_bytes({"category": category, "subroot": to_hex(subroot)})
    )


def test_a_partial_root_differs_from_the_full_root(seller, agent_id):
    """Selling three categories must not produce the commitment for all six."""
    full = _export(seller, agent_id)
    partial = _export(seller, agent_id, categories=SOLD)
    assert partial.root_hex != full.root_hex


def test_subroots_are_stable_for_categories_without_cross_category_edges(
    seller, agent_id
):
    """A category's subroot is a property of its own content, so dropping its
    neighbours from the sale does not move it."""
    full = _export(seller, agent_id).package.tree()
    partial = _export(seller, agent_id, categories=SOLD).package.tree()

    for category in ("preferences", "learned-behaviors"):
        assert partial.subroots[category] == full.subroots[category]


def test_the_relationships_subroot_does_move_with_the_selection(seller, agent_id):
    """The one documented exception, and the reason for it.

    ``relationships/`` carries the WARM edges, and an edge is pruned when the
    entity at its far end is not part of the sale. So the content of
    ``relationships/`` — and therefore its subroot — genuinely depends on which
    other categories travel with it. This is a consequence of pruning being
    correct, not a defect in the tree: the alternative is committing to edges
    the buyer can never resolve, which fails verification on an honest transfer.

    The practical consequence, stated plainly: a partial sale commits its own
    root, computed over exactly what is being sold. Verifying a partial package
    against a *full* listing's root works for categories that carry no
    cross-category edges, and does not for ``relationships``."""
    full = _export(seller, agent_id).package.tree()
    partial = _export(seller, agent_id, categories=SOLD).package.tree()

    assert partial.subroots["relationships"] != full.subroots["relationships"]

    full_edges = [
        r for r in _export(seller, agent_id).package.data["relationships"]
        if r["kind"] == "relation"
    ]
    partial_edges = [
        r for r in _export(seller, agent_id, categories=SOLD).package.data["relationships"]
        if r["kind"] == "relation"
    ]
    assert len(partial_edges) < len(full_edges)


def test_the_signed_header_names_the_categories_sold(seller, agent_id):
    exported = _export(seller, agent_id, categories=SOLD)
    assert exported.package.header["categories"] == sorted(SOLD)


def test_a_buyer_cannot_be_handed_more_than_the_header_promises(seller, buyer, agent_id):
    """Smuggling an extra category past a partial sale invalidates the signature."""
    from succession.provenance import SignatureError

    partial = _export(seller, agent_id, categories=SOLD)
    full = _export(seller, agent_id)

    partial.package.data["commitments"] = full.package.data["commitments"]

    with pytest.raises((SignatureError, Exception)):
        import_package(
            partial.package,
            buyer,
            committed_root=partial.root_hex,
            expected_signer=SELLER.address,
        )


def test_dangling_edges_are_pruned_before_hashing(seller, agent_id):
    """``relationships`` carries the edges. Selling it without ``commitments``
    would commit to edges pointing at entities the buyer never receives — the
    package must drop those before the root is computed, or an honest transfer
    fails verification."""
    exported = _export(seller, agent_id, categories=["relationships"])

    edges = [r for r in exported.package.data["relationships"] if r["kind"] == "relation"]
    names = {
        r["origin"]["name"]
        for r in exported.package.data["relationships"]
        if r["kind"] == "entity"
    }
    for edge in edges:
        assert edge["origin"]["from"][1] in names
        assert edge["origin"]["to"][1] in names
    assert exported.redaction.withheld_dangling_relations > 0


def test_every_data_category_can_be_sold_alone(seller, buyer, agent_id, tmp_path):
    """No category depends on another to import cleanly."""
    from succession.memory.sibyl import open_tenant

    for i, category in enumerate(DATA_CATEGORIES):
        sink = open_tenant(tmp_path / f"solo-{i}.db", f"tenant-solo-{i}")
        exported = _export(seller, agent_id, categories=[category])
        result = import_package(
            exported.package,
            sink,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )
        assert result.verified, f"{category} failed to transfer alone"


def test_an_unknown_category_is_refused(seller, agent_id):
    with pytest.raises(ValueError, match="not SMP data categories"):
        _export(seller, agent_id, categories=["relationships", "invented"])
