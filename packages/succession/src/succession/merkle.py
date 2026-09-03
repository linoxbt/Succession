"""Merkle tree over an SMP package, with per-category subroots.

Why a tree and not a flat hash: Part 6 of the spec wants *partial* succession —
transferring, say, ``relationships`` and ``preferences`` but not
``commitments``. If the integrity commitment is one flat hash over everything,
a partial transfer cannot be verified against it without redesigning the
scheme. Committing a subroot per SMP category means a buyer who receives three
of six categories can still verify each one against the root that was posted
on-chain at listing time.

Construction (RFC 6962 domain separation):

    leaf(data)        = keccak256(0x00 || data)
    node(left, right) = keccak256(0x01 || left || right)

The distinct leaf and node prefixes are what stop the classic second-preimage
attack, where an attacker presents an internal node as if it were a leaf. An
odd node at any level is promoted unchanged to the next level rather than
duplicated — duplication is the other well-known forgery vector, since it makes
two different leaf multisets produce the same root.

The tree is two-level by construction:

* a subtree per SMP category, over that category's leaves in canonical order
* the root, over the ``(category, subroot)`` pairs in category-name order

Committing the category name alongside its subroot is deliberate. Without it, a
seller could relabel a cheap category as an expensive one and the root would
not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from eth_utils import keccak

from .canonical import canonical_bytes

__all__ = [
    "EMPTY",
    "MerkleTree",
    "CategoryTree",
    "hash_leaf",
    "hash_node",
    "build_tree",
    "verify_proof",
    "to_hex",
    "from_hex",
]

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"

#: The root of an empty set. Distinct from any real root, and stable.
EMPTY = keccak(b"succession:smp:empty")


def to_hex(digest: bytes) -> str:
    return "0x" + digest.hex()


def from_hex(value: str) -> bytes:
    raw = value[2:] if value.startswith("0x") else value
    digest = bytes.fromhex(raw)
    if len(digest) != 32:
        raise ValueError(f"expected a 32-byte digest, got {len(digest)} bytes")
    return digest


def hash_leaf(data: bytes) -> bytes:
    return keccak(LEAF_PREFIX + data)


def hash_node(left: bytes, right: bytes) -> bytes:
    return keccak(NODE_PREFIX + left + right)


def _fold(level: list[bytes]) -> bytes:
    """Fold a list of leaf digests into a single root."""
    if not level:
        return EMPTY
    while len(level) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(level) - 1, 2):
            nxt.append(hash_node(level[i], level[i + 1]))
        if len(level) % 2:
            # Promote the odd node unchanged. Never duplicate it.
            nxt.append(level[-1])
        level = nxt
    return level[0]


def _proof_path(level: list[bytes], index: int) -> list[tuple[str, bytes]]:
    """Sibling path from ``index`` up to the root, as (side, digest) pairs."""
    if index < 0 or index >= len(level):
        raise IndexError(f"leaf index {index} out of range for {len(level)} leaves")
    path: list[tuple[str, bytes]] = []
    while len(level) > 1:
        nxt: list[bytes] = []
        new_index = index
        for i in range(0, len(level) - 1, 2):
            nxt.append(hash_node(level[i], level[i + 1]))
            if i == index:
                path.append(("right", level[i + 1]))
                new_index = len(nxt) - 1
            elif i + 1 == index:
                path.append(("left", level[i]))
                new_index = len(nxt) - 1
        if len(level) % 2:
            nxt.append(level[-1])
            if index == len(level) - 1:
                # Promoted: no sibling at this level, position is the new last.
                new_index = len(nxt) - 1
        level = nxt
        index = new_index
    return path


@dataclass(frozen=True)
class CategoryTree:
    """One SMP category's subtree."""

    category: str
    leaves: tuple[bytes, ...]
    subroot: bytes

    @property
    def count(self) -> int:
        return len(self.leaves)

    def proof(self, index: int) -> list[tuple[str, bytes]]:
        return _proof_path(list(self.leaves), index)


@dataclass(frozen=True)
class MerkleTree:
    """The full two-level tree over an SMP package."""

    categories: tuple[CategoryTree, ...]
    root: bytes

    @property
    def subroots(self) -> dict[str, bytes]:
        return {c.category: c.subroot for c in self.categories}

    @property
    def leaf_count(self) -> int:
        return sum(c.count for c in self.categories)

    def category(self, name: str) -> CategoryTree:
        for c in self.categories:
            if c.category == name:
                return c
        raise KeyError(f"no such category in tree: {name}")

    def to_manifest(self) -> dict[str, Any]:
        """The serializable integrity-proof document shipped inside the package."""
        return {
            "algorithm": "keccak256",
            "construction": "rfc6962-domain-separated",
            "root": to_hex(self.root),
            "leaf_count": self.leaf_count,
            "categories": [
                {
                    "category": c.category,
                    "subroot": to_hex(c.subroot),
                    "leaf_count": c.count,
                }
                for c in self.categories
            ],
        }

    def category_proof(self, name: str) -> list[tuple[str, bytes]]:
        """Sibling path proving one category's subroot is under the root.

        This is what lets a partial-succession buyer verify the categories they
        actually received against the root committed at listing time, without
        ever seeing the categories they did not buy.
        """
        pairs = [_category_pair_leaf(c.category, c.subroot) for c in self.categories]
        index = next(
            i for i, c in enumerate(self.categories) if c.category == name
        )
        return _proof_path(pairs, index)


def _category_pair_leaf(category: str, subroot: bytes) -> bytes:
    """Bind a category name to its subroot so the label cannot be swapped."""
    return hash_leaf(canonical_bytes({"category": category, "subroot": to_hex(subroot)}))


def build_tree(leaves_by_category: dict[str, Sequence[bytes]]) -> MerkleTree:
    """Build the two-level tree.

    ``leaves_by_category`` maps an SMP category name to that category's already
    canonicalized leaf payloads, **in canonical order**. Ordering is the
    caller's responsibility because only the caller knows whether a category
    sorts by ``(category, name)`` or by ``(ts, id)``.
    """
    trees: list[CategoryTree] = []
    for category in sorted(leaves_by_category):
        digests = tuple(hash_leaf(item) for item in leaves_by_category[category])
        trees.append(
            CategoryTree(
                category=category,
                leaves=digests,
                subroot=_fold(list(digests)),
            )
        )
    pairs = [_category_pair_leaf(t.category, t.subroot) for t in trees]
    return MerkleTree(categories=tuple(trees), root=_fold(pairs))


def verify_proof(leaf: bytes, path: Iterable[tuple[str, bytes]], root: bytes) -> bool:
    """Recompute a root from a leaf digest and its sibling path."""
    node = leaf
    for side, sibling in path:
        if side == "left":
            node = hash_node(sibling, node)
        elif side == "right":
            node = hash_node(node, sibling)
        else:
            raise ValueError(f"invalid proof side {side!r}")
    return node == root
