"""Reputation that a buyer recomputes rather than a seller supplies.

The property under test throughout is that the score is *derived*. A seller
cannot raise it by asserting anything, because nothing they assert is an input:
every factor reads either the provenance chain, which only grows when a
settlement verified, or records already covered by the Merkle tree.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from succession.redaction import Consent, Sensitivity, mark, read_disclosure
from succession.reputation import (
    read_lineage,
    score_lineage,
    score_package,
)

NOW = datetime(2026, 9, 5, tzinfo=timezone.utc)


def link(owner: str, days_ago: int, version: int | None = None, digest: str = "aa"):
    entry = {
        "owner": owner,
        "acquired_at": (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verified_hash": "0x" + digest * 32,
    }
    if version is not None:
        entry["memory_version"] = version
    return entry


# --- the shape of the score ---------------------------------------------


def test_an_origin_memory_is_unproven_rather_than_bad():
    """Never transferred is not a failing. It scores neutral, not zero."""
    result = score_lineage(read_lineage([]), now=NOW)
    assert result.grade == "early"
    assert 0 < result.score < 50
    integrity = next(f for f in result.factors if f.name == "integrity_record")
    assert "unproven rather than poor" in integrity.explanation


def test_a_deep_verified_lineage_scores_higher_than_a_shallow_one():
    shallow = score_lineage(read_lineage([link("a", 30, 10)]), now=NOW)
    deep = score_lineage(
        read_lineage([link("a", 400, 10), link("b", 200, 40), link("c", 60, 90)]),
        now=NOW,
    )
    assert deep.score > shallow.score
    assert deep.grade in ("proven", "established")


def test_a_malformed_chain_entry_does_not_count_as_a_handover():
    """A link without a usable hash is not evidence, so it cannot inflate depth."""
    good = score_lineage(read_lineage([link("a", 100, 5)]), now=NOW)
    padded = score_lineage(
        read_lineage(
            [
                link("a", 100, 5),
                {"owner": "", "acquired_at": "", "verified_hash": "0xnope"},
                {"owner": "ghost", "acquired_at": "", "verified_hash": ""},
            ]
        ),
        now=NOW,
    )
    # Three entries, one sound: depth is unchanged and integrity is *worse*,
    # so padding the chain with junk lowers the score rather than raising it.
    assert padded.score < good.score


def test_factors_report_the_inputs_they_were_computed_from():
    """A score nobody can audit is a score nobody should believe."""
    result = score_lineage(read_lineage([link("a", 90, 12)]), now=NOW)
    for factor in result.factors:
        assert factor.explanation
        assert isinstance(factor.inputs, dict)
    assert sum(f.weight for f in result.factors) == 1


# --- continuity ----------------------------------------------------------


def test_growing_the_memory_scores_above_sitting_on_it():
    chain = [link("a", 120, 10)]
    grew = score_lineage(read_lineage(chain), current_version=60, now=NOW)
    sat = score_lineage(read_lineage(chain), current_version=10, now=NOW)
    assert grew.score > sat.score


def test_continuity_abstains_when_there_is_nothing_to_compare():
    """An entry from before versions were recorded is not scored zero for it."""
    result = score_lineage(read_lineage([link("a", 90)]), current_version=None, now=NOW)
    factor = next(f for f in result.factors if f.name == "continuity")
    assert factor.value == pytest.approx(0.5, abs=0.001)
    assert "abstains" in factor.explanation


# --- earnings ------------------------------------------------------------


def test_earnings_abstain_below_the_floor():
    """A rate over three jobs is not a rate."""
    result = score_lineage(
        read_lineage([link("a", 90, 5)]), resolved_jobs=3, completed_jobs=3, now=NOW
    )
    factor = next(f for f in result.factors if f.name == "earnings_record")
    assert factor.value == pytest.approx(0.5, abs=0.001)


def test_earnings_count_once_there_are_enough_of_them():
    strong = score_lineage(
        read_lineage([link("a", 90, 5)]), resolved_jobs=10, completed_jobs=10, now=NOW
    )
    weak = score_lineage(
        read_lineage([link("a", 90, 5)]), resolved_jobs=10, completed_jobs=2, now=NOW
    )
    assert strong.score > weak.score


# --- derivation from a real package --------------------------------------


def test_the_score_comes_out_of_the_package_a_buyer_received(seller, agent_id):
    """The buyer recomputes it from what they hold, like the root."""
    from succession.export import export_tenant

    export = export_tenant(
        seller,
        agent_identity=agent_id,
        private_key="0x" + "11" * 32,
        provenance_chain=[link("prior-owner", 200, 3)],
    )
    result = score_package(export.package, now=NOW)
    assert result.links == 1
    assert result.score > 0
    assert "Recomputed" in result.to_dict()["basis"]


def test_a_seller_cannot_assert_a_score_into_the_package(seller, agent_id):
    """There is no field to put one in. The header carries no reputation."""
    from succession.export import export_tenant

    export = export_tenant(
        seller, agent_identity=agent_id, private_key="0x" + "11" * 32
    )
    assert "reputation" not in export.package.header
    assert "score" not in export.package.header


# --- consent -------------------------------------------------------------


def test_a_record_without_consent_never_reaches_the_tree():
    """The counterparty gate is enforced before hashing, like transferability."""
    withheld = read_disclosure(mark({"company": "X"}, consent=Consent.WITHHELD))
    assert withheld.may_transfer is False
    assert withheld.preview_countable is False


def test_the_default_basis_lets_ordinary_records_move():
    """An unflagged record is contractual, so nothing breaks by omission."""
    plain = read_disclosure({"company": "X"})
    assert plain.consent == Consent.CONTRACTUAL
    assert plain.may_transfer is True


def test_both_gates_are_independent():
    """Either one alone stops a record."""
    no_consent = read_disclosure(
        mark({"a": 1}, transferable=True, consent=Consent.WITHHELD)
    )
    not_transferable = read_disclosure(
        mark({"a": 1}, transferable=False, consent=Consent.EXPLICIT)
    )
    assert no_consent.may_transfer is False
    assert not_transferable.may_transfer is False


def test_an_unknown_basis_is_refused_rather_than_ignored():
    with pytest.raises(ValueError, match="unknown consent basis"):
        read_disclosure({"_succession": {"consent": "vibes"}})


def test_withheld_records_are_counted_separately_in_the_report():
    """A buyer can tell a seller's own redaction from a counterparty's refusal."""
    from succession.redaction import filter_transferable

    records = [
        {"body": mark({"a": 1}, consent=Consent.WITHHELD)},
        {"body": mark({"b": 2}, transferable=False)},
        {"body": {"c": 3}},
    ]
    kept, by_flag, by_consent = filter_transferable(records)
    assert len(kept) == 1
    assert by_flag == 1
    assert by_consent == 1


def test_the_permissions_document_reports_consent_rather_than_asserting_it(
    seller, agent_id
):
    from succession.export import export_tenant

    export = export_tenant(
        seller, agent_identity=agent_id, private_key="0x" + "11" * 32
    )
    consent = export.package.permissions["consent"]
    assert "withheld_without_consent" in consent
    assert "operator_responsibility" in consent


# --- ACP handover --------------------------------------------------------


def test_the_handover_states_that_it_transfers_nothing():
    """The honest part is the disclaimer, and it is in the signed payload."""
    from succession.acp import build_handover, verify_handover

    handover = build_handover(
        agent_identity="erc8004:84532:417",
        entity_id=42,
        agent_wallet="0x" + "11" * 20,
        buyer_identity="erc8004:84532:1183",
        buyer_address="0x" + "22" * 20,
        settlement_reference="0xabc",
        verified_hash="0x" + "cd" * 32,
        private_key="0x" + "11" * 32,
    )
    assert handover["transfers_registration"] is False
    assert "cannot be reassigned" in handover["note"]
    # Signed, so its origin is checkable even though its claim is limited.
    assert verify_handover(handover).startswith("0x")


def test_a_tampered_handover_does_not_recover_to_the_signer():
    from succession.acp import build_handover, verify_handover

    handover = build_handover(
        agent_identity="erc8004:84532:417",
        entity_id=42,
        agent_wallet="0x" + "11" * 20,
        buyer_identity="erc8004:84532:1183",
        buyer_address="0x" + "22" * 20,
        settlement_reference="0xabc",
        verified_hash="0x" + "cd" * 32,
        private_key="0x" + "11" * 32,
    )
    signer = verify_handover(handover)
    forged = {**handover, "succeeded_by": "erc8004:84532:9999"}
    assert verify_handover(forged) != signer
