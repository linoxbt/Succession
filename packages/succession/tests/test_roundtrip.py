"""The Day 1-2 gate: export tenant A, import into tenant B, prove they match.

The spec is blunt about this one — do not proceed past this until it passes
reliably. Everything downstream (escrow release, the seal, the certificate)
assumes these two tests hold.
"""

from __future__ import annotations

import copy

import pytest

from succession import export_tenant, import_package
from succession.importer import ImportError_, IntegrityMismatch
from succession.merkle import to_hex
from succession.smp import DATA_CATEGORIES, SMPPackage

from succession.demokeys import BUYER, SELLER


def _export(seller, agent_id, **kw):
    return export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key, **kw
    )


def test_export_import_reproduces_the_committed_root(seller, buyer, agent_id):
    """A → package → B, re-hashed on B, matches the root committed at listing."""
    exported = _export(seller, agent_id)
    committed = exported.root_hex

    result = import_package(
        exported.package,
        buyer,
        committed_root=committed,
        expected_signer=SELLER.address,
    )

    assert result.verified
    assert result.committed_root == result.delivered_root == result.reimported_root
    assert result.total_records == exported.record_count
    assert result.signer.lower() == SELLER.address.lower()


def test_every_tier_survives_the_transfer(seller, buyer, agent_id):
    """A partial transfer that silently drops a tier would still hash-match if the
    commitment were computed after the loss. It is computed before, so it cannot."""
    exported = _export(seller, agent_id)
    import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )

    assert len(buyer.entities()) == len(
        [e for e in seller.entities() if e["name"] != "ironwood-defense-logistics"]
    )
    assert len(buyer.events()) == len(seller.events())
    assert len(buyer.states()) == len(seller.states())
    assert len(buyer.references()) == len(seller.references())
    assert len(buyer.archived()) == len(seller.archived())
    assert len(buyer.relations()) == len(seller.relations())


def test_the_in_flight_commitment_arrives(seller, buyer, agent_id):
    """The cutover beat, asserted rather than demonstrated: the buyer's cold store
    holds the open quote and the live working position the seller left mid-flight."""
    exported = _export(seller, agent_id)
    import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )

    quote = buyer.client.get_entity("commitment", "quote-NW-4471")
    assert quote["body"]["quoted_rate_usd"] == 2380
    assert quote["body"]["status"] == "open"

    position = buyer.client.get_state("current-negotiation")["body"]
    assert position["counterparty"] == "Northwind Mills"
    assert "Monday" in position["our_position"]


def test_export_is_deterministic(seller, agent_id):
    """Two exports of an unchanged tenant produce byte-identical commitments.

    Determinism is the whole premise of hashing a memory store. If this ever
    fails, every other guarantee in the system is decoration."""
    first = _export(seller, agent_id, created_at="2026-09-05T10:14:02Z")
    second = _export(seller, agent_id, created_at="2026-09-05T10:14:02Z")

    assert first.root_hex == second.root_hex
    assert first.package.header == second.package.header
    assert first.package.integrity == second.package.integrity


def test_package_survives_a_disk_round_trip(seller, agent_id, tmp_path):
    """The nine directories on disk are the wire format, not just an in-memory object."""
    exported = _export(seller, agent_id)
    exported.package.write_dir(tmp_path / "pkg")

    reloaded = SMPPackage.read_dir(tmp_path / "pkg")

    assert to_hex(reloaded.tree().root) == exported.root_hex
    assert reloaded.header == exported.package.header
    for category in DATA_CATEGORIES:
        assert (tmp_path / "pkg" / category).is_dir()
    for generated in ("provenance", "permissions", "integrity-proof"):
        assert (tmp_path / "pkg" / generated).is_dir()


# -- the corruption tests -------------------------------------------------


def test_a_corrupted_entity_is_caught(seller, buyer, agent_id):
    """Deliberately corrupt one entity in transit; the mismatch must be caught."""
    exported = _export(seller, agent_id)
    committed = exported.root_hex

    tampered = copy.deepcopy(exported.package)
    for record in tampered.data["relationships"]:
        if record["kind"] == "entity" and record["origin"]["name"] == "northwind-mills":
            record["body"]["note"] = "Books Mondays."
            break
    else:
        pytest.fail("seed data no longer contains the entity this test corrupts")

    with pytest.raises(IntegrityMismatch) as exc:
        import_package(
            tampered,
            buyer,
            committed_root=committed,
            expected_signer=SELLER.address,
        )
    assert exc.value.committed != exc.value.delivered
    assert buyer.is_empty(), "a rejected package must not leave partial writes behind"


def test_a_dropped_record_is_caught(seller, buyer, agent_id):
    exported = _export(seller, agent_id)
    tampered = copy.deepcopy(exported.package)
    tampered.data["history"].pop()

    with pytest.raises(IntegrityMismatch):
        import_package(
            tampered,
            buyer,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )


def test_an_added_record_is_caught(seller, buyer, agent_id):
    exported = _export(seller, agent_id)
    tampered = copy.deepcopy(exported.package)
    tampered.data["preferences"].append(
        {
            "kind": "entity",
            "origin": {"tier": "entity", "category": "preference", "name": "injected"},
            "status": None,
            "body": {"margin_floor_pct": 0},
        }
    )

    with pytest.raises(IntegrityMismatch):
        import_package(
            tampered,
            buyer,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )


def test_a_forged_signature_is_caught(seller, buyer, agent_id):
    """Right content, wrong signer: the buyer is receiving someone else's memory."""
    from succession.provenance import sign_header

    exported = _export(seller, agent_id)
    tampered = copy.deepcopy(exported.package)
    tampered.header = sign_header(
        {**tampered.header, "signature": None}, BUYER.private_key
    )

    from succession.provenance import SignatureError

    with pytest.raises(SignatureError):
        import_package(
            tampered,
            buyer,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )


def test_a_relabelled_agent_identity_is_caught(seller, buyer, agent_id):
    """The signature covers the whole header, so swapping the agent it claims to
    be invalidates it — even though the memory itself is untouched."""
    from succession.provenance import SignatureError

    exported = _export(seller, agent_id)
    tampered = copy.deepcopy(exported.package)
    tampered.header["agent_identity"] = "erc8004:84532:9999"

    with pytest.raises(SignatureError):
        import_package(
            tampered,
            buyer,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )


def test_import_refuses_a_non_empty_tenant(seller, buyer, agent_id):
    """Importing over existing memory would silently update rows on collision."""
    exported = _export(seller, agent_id)
    buyer.client.set_entity("preference", "pre-existing", {"x": 1})

    with pytest.raises(ImportError_, match="fresh tenant"):
        import_package(
            exported.package,
            buyer,
            committed_root=exported.root_hex,
            expected_signer=SELLER.address,
        )
