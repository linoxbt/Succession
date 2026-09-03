"""The integrity scheme's own properties, tested away from the pipeline."""

from __future__ import annotations

import pytest

from succession.canonical import CanonicalizationError, canonical_bytes, canonical_json
from succession.merkle import (
    EMPTY,
    build_tree,
    hash_leaf,
    hash_node,
    to_hex,
    verify_proof,
)


def _leaves(n, prefix=b"x"):
    return [prefix + bytes([i]) for i in range(n)]


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 5, 7, 8, 9, 16, 17, 33])
def test_every_leaf_proves_against_the_subroot(n):
    tree = build_tree({"a": _leaves(n)})
    category = tree.category("a")
    for i, leaf in enumerate(category.leaves):
        assert verify_proof(leaf, category.proof(i), category.subroot)


def test_an_empty_category_has_a_distinct_stable_root():
    tree = build_tree({"a": []})
    assert tree.category("a").subroot == EMPTY


def test_leaves_and_nodes_are_domain_separated():
    """Without distinct prefixes, an internal node could be presented as a leaf."""
    left, right = hash_leaf(b"l"), hash_leaf(b"r")
    node = hash_node(left, right)
    assert node != hash_leaf(left + right)


def test_an_odd_node_is_promoted_not_duplicated():
    """Duplicating the odd node would make two different leaf sets share a root."""
    three = build_tree({"a": _leaves(3)}).category("a").subroot
    duplicated = build_tree({"a": [*_leaves(3), _leaves(3)[2]]}).category("a").subroot
    assert three != duplicated


def test_reordering_leaves_changes_the_root():
    forward = build_tree({"a": _leaves(6)}).root
    backward = build_tree({"a": list(reversed(_leaves(6)))}).root
    assert forward != backward


def test_relabelling_a_category_changes_the_root():
    """The category name is bound to its subroot, so a cheap directory cannot be
    passed off as an expensive one."""
    a = build_tree({"relationships": _leaves(4)}).root
    b = build_tree({"commitments": _leaves(4)}).root
    assert a != b


def test_moving_a_leaf_between_categories_changes_the_root():
    a = build_tree({"x": _leaves(4), "y": _leaves(2, b"y")})
    b = build_tree({"x": _leaves(3), "y": [*_leaves(2, b"y"), _leaves(4)[3]]})
    assert a.root != b.root


def test_category_order_does_not_matter():
    a = build_tree({"x": _leaves(3), "y": _leaves(2, b"y")}).root
    b = build_tree({"y": _leaves(2, b"y"), "x": _leaves(3)}).root
    assert a == b


def test_a_category_proof_verifies_against_the_root():
    tree = build_tree({"x": _leaves(3), "y": _leaves(5, b"y"), "z": _leaves(1, b"z")})
    from succession.merkle import hash_leaf as leaf

    for name in ("x", "y", "z"):
        pair = leaf(
            canonical_bytes({"category": name, "subroot": to_hex(tree.subroots[name])})
        )
        assert verify_proof(pair, tree.category_proof(name), tree.root)


def test_a_bad_proof_fails():
    tree = build_tree({"a": _leaves(8)})
    category = tree.category("a")
    proof = category.proof(3)
    tampered = [(side, bytes(32)) for side, _ in proof]
    assert not verify_proof(category.leaves[3], tampered, category.subroot)


def test_manifest_reports_the_shape():
    tree = build_tree({"a": _leaves(3), "b": _leaves(2, b"b")})
    manifest = tree.to_manifest()
    assert manifest["algorithm"] == "keccak256"
    assert manifest["leaf_count"] == 5
    assert {c["category"] for c in manifest["categories"]} == {"a", "b"}


# -- canonicalization -----------------------------------------------------


def test_key_order_does_not_change_the_bytes():
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})


def test_list_order_does_change_the_bytes():
    assert canonical_bytes([1, 2]) != canonical_bytes([2, 1])


def test_unicode_is_nfc_normalized():
    composed = "café"        # é as one code point
    decomposed = "café"     # e + combining acute
    assert composed != decomposed
    assert canonical_bytes({"k": composed}) == canonical_bytes({"k": decomposed})


def test_floats_are_refused():
    with pytest.raises(CanonicalizationError, match="floats"):
        canonical_bytes({"rate": 1.5})


def test_non_string_keys_are_refused():
    with pytest.raises(CanonicalizationError, match="keys must be strings"):
        canonical_bytes({1: "a"})


def test_a_key_collision_after_normalization_is_refused():
    with pytest.raises(CanonicalizationError, match="duplicate key"):
        canonical_bytes({"café": 1, "café": 2})


def test_output_has_no_incidental_whitespace():
    assert canonical_json({"a": [1, 2], "b": {"c": 3}}) == '{"a":[1,2],"b":{"c":3}}'
