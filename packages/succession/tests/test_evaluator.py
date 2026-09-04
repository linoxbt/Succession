"""The Evaluator — the arbiter that re-derives instead of trusting.

The test that matters most here is
``test_a_dishonest_buyer_cannot_steal_by_claiming_a_mismatch``: it walks the
exact attack ``ListingContract``'s docstring admits it cannot stop on its own,
and shows the evaluator stopping it. Everything else exists to keep that one
honest — in particular ``test_evaluator_does_not_take_the_buyers_word``, which
would still pass if the evaluator simply echoed whatever root it was handed, so
it is written to fail in that case.
"""

from __future__ import annotations

import pytest
from eth_account import Account

from succession.dataroom import build_preview
from succession.demokeys import BUYER, SELLER
from succession.evaluator import (
    EVALUATION_DOMAIN,
    Evaluator,
    Verdict,
    verify_verdict,
)
from succession.importer import import_package
from succession.provenance import SignatureError
from succession.seal import SealRegistry
from succession.settlement import LocalSettlement, SettlementError
from succession.transfer import list_asset

ARBITER_KEY = "0x" + "a7" * 32
ARBITER = Account.from_key(ARBITER_KEY).address
AGENT = "erc8004:84532:0417"
BUYER_AGENT = "erc8004:84532:1183"
PRICE = 420_000_000


@pytest.fixture
def evaluator():
    return Evaluator(ARBITER_KEY)


@pytest.fixture
def sale(tmp_path, seller, buyer):
    """A listing funded into escrow, with the package delivered and imported."""
    settlement = LocalSettlement(tmp_path / "settlement.db", arbiter=ARBITER)
    listed = list_asset(
        seller,
        settlement,
        listing_id="listing-0417",
        agent_identity=AGENT,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=PRICE,
    )
    settlement.buy("listing-0417", buyer=BUYER.address, amount=PRICE)
    import_package(
        listed.export.package,
        buyer,
        committed_root=listed.committed_root,
        expected_signer=SELLER.address,
    )
    return settlement, listed


# -- independence ---------------------------------------------------------


def test_evaluator_does_not_take_the_buyers_word(evaluator, sale, buyer):
    """The root must come from the store, not from an argument.

    `re_derive_root` is given only the buyer's tenant. If it were echoing an
    asserted value there would be nothing for it to echo.
    """
    _, listed = sale

    derived = evaluator.re_derive_root(buyer, categories=list(listed.export.package.data))

    assert derived == listed.committed_root


def test_re_derived_root_is_wrong_when_the_store_is_wrong(evaluator, sale, buyer):
    """Mutating the buyer's store must move the evaluator's root."""
    _, listed = sale
    buyer.client.set_entity("relationship", "tampered", {"note": "not in the package"})

    derived = evaluator.re_derive_root(buyer, categories=list(listed.export.package.data))

    assert derived != listed.committed_root


# -- the verdict ----------------------------------------------------------


def test_a_clean_delivery_verifies(evaluator, sale, buyer):
    settlement, listed = sale

    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    assert verdict.verified
    assert verdict.evaluator_root == listed.committed_root
    assert verdict.evaluator == ARBITER
    assert {f.check for f in verdict.findings} == {"integrity-root", "seller-signature"}


def test_verdict_is_signed_and_recoverable(evaluator, sale, buyer):
    _, listed = sale

    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    assert verify_verdict(verdict, expected_evaluator=ARBITER) == ARBITER


def test_verdict_signature_is_domain_separated(evaluator, sale, buyer):
    """A verdict must never be replayable as a provenance attestation."""
    _, listed = sale
    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    assert verdict.signing_preimage().startswith(EVALUATION_DOMAIN + "\n")


def test_a_tampered_verdict_fails_recovery(evaluator, sale, buyer):
    _, listed = sale
    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )
    forged = Verdict(
        listing_id=verdict.listing_id,
        committed_root=verdict.committed_root,
        evaluator_root="0x" + "ff" * 32,
        findings=verdict.findings,
        evaluator=verdict.evaluator,
        evaluated_at=verdict.evaluated_at,
        signature=verdict.signature,
    )

    with pytest.raises(SignatureError):
        verify_verdict(forged, expected_evaluator=ARBITER)


def test_unsigned_verdict_is_refused(evaluator):
    bare = Verdict(
        listing_id="l",
        committed_root="0x" + "00" * 32,
        evaluator_root="0x" + "00" * 32,
        findings=(),
        evaluator=ARBITER,
        evaluated_at="2026-09-04T00:00:00Z",
    )
    with pytest.raises(SignatureError, match="no signature"):
        verify_verdict(bare)


def test_a_forged_signer_is_caught(evaluator, sale, buyer):
    _, listed = sale
    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=BUYER.address,  # not who signed the package
    )

    assert not verdict.verified
    signature_finding = next(
        f for f in verdict.findings if f.check == "seller-signature"
    )
    assert not signature_finding.passed


# -- the preview audit ----------------------------------------------------


def test_preview_audit_passes_on_honest_figures(evaluator, seller):
    """Audited against the seller's tenant — the store the data room described."""
    claimed = build_preview(seller, agent_identity=AGENT).to_dict()

    findings = evaluator.check_preview(seller, claimed, agent_identity=AGENT)

    assert findings and all(f.passed for f in findings)


def test_preview_audit_catches_an_overstated_asset(evaluator, seller):
    """Intact delivery, false prospectus. Only this check sees it."""
    inflated = {"counts": {"relationship": 9999}, "memory_size_bytes": 99_999_999}

    findings = evaluator.check_preview(seller, inflated, agent_identity=AGENT)

    assert findings and not all(f.passed for f in findings)


def test_preview_audit_must_not_be_pointed_at_the_buyers_store(
    evaluator, sale, buyer, seller
):
    """The mistake this API is shaped to prevent.

    Withheld non-transferable records mean an honest delivery leaves the buyer
    with legitimately less than the preview described. Comparing those two
    reports fraud on a correct sale, so `evaluate()` does not do it and this
    test pins the difference that makes it wrong.
    """
    claimed = build_preview(seller, agent_identity=AGENT).to_dict()

    against_buyer = evaluator.check_preview(buyer, claimed, agent_identity=AGENT)

    assert not all(f.passed for f in against_buyer)


def test_audit_listing_produces_a_signed_pre_purchase_verdict(evaluator, seller):
    """What a buyer reads before funding escrow."""
    claimed = build_preview(seller, agent_identity=AGENT).to_dict()

    verdict = evaluator.audit_listing(
        seller, claimed, listing_id="listing-0417", agent_identity=AGENT
    )

    assert verdict.verified
    assert verify_verdict(verdict, expected_evaluator=ARBITER) == ARBITER


def test_audit_listing_flags_a_false_prospectus(evaluator, seller):
    verdict = evaluator.audit_listing(
        seller,
        {"memory_size_bytes": 99_999_999},
        listing_id="listing-0417",
        agent_identity=AGENT,
    )

    assert not verdict.verified
    assert "preview:memory_size_bytes" in verdict.summary()


# -- settlement as arbiter ------------------------------------------------


def test_arbiter_settles_a_clean_delivery(evaluator, sale, buyer):
    settlement, listed = sale
    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    receipt = evaluator.settle(settlement, verdict, buyer_identity=BUYER_AGENT)

    assert receipt.outcome == "released"
    assert receipt.confirmed_by == "arbiter"


def test_a_dishonest_buyer_cannot_steal_by_claiming_a_mismatch(
    evaluator, sale, buyer
):
    """The attack the contract admits it cannot stop alone.

    A buyer who received a perfectly good package submits a wrong hash to
    trigger the automatic refund and keep the memory. When the evaluator
    settles instead, the root that reaches the contract is the one the
    evaluator derived from the buyer's own store — so the escrow releases to
    the seller and the theft does not happen.
    """
    settlement, listed = sale

    # What the dishonest buyer would have submitted.
    buyers_false_claim = "0x" + "de" * 32
    assert buyers_false_claim != listed.committed_root

    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )
    receipt = evaluator.settle(settlement, verdict, buyer_identity=BUYER_AGENT)

    assert verdict.evaluator_root == listed.committed_root
    assert receipt.outcome == "released"
    assert receipt.paid_to == SELLER.address


def test_arbiter_refuses_to_rubber_stamp_a_corrupt_delivery(
    evaluator, sale, buyer
):
    """The evaluator is not a rubber stamp in the other direction either."""
    settlement, listed = sale
    buyer.client.set_entity("relationship", "smuggled", {"note": "extra"})

    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )
    receipt = evaluator.settle(settlement, verdict, buyer_identity=BUYER_AGENT)

    assert not verdict.verified
    assert receipt.outcome == "refunded"


def test_a_stranger_cannot_confirm(sale, buyer):
    """Only the buyer and the arbiter, exactly as the contract enforces."""
    settlement, listed = sale
    stranger = Evaluator("0x" + "b9" * 32)
    verdict = stranger.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    with pytest.raises(SettlementError, match="neither the buyer nor the arbiter"):
        stranger.settle(settlement, verdict, buyer_identity=BUYER_AGENT)


def test_buyer_confirmation_is_still_labelled_as_self_reported(sale):
    """The default path must not silently claim the arbiter's credibility."""
    settlement, listed = sale

    receipt = settlement.confirm_transfer(
        "listing-0417",
        delivered_hash=listed.committed_root,
        buyer_identity=BUYER_AGENT,
    )

    assert receipt.confirmed_by == "buyer"


# -- partial sales --------------------------------------------------------


def test_evaluation_respects_a_partial_sale_scope(tmp_path, seller, buyer):
    """Re-deriving over all six categories would fail an honest partial sale."""
    settlement = LocalSettlement(tmp_path / "settlement.db", arbiter=ARBITER)
    categories = ["relationships", "preferences"]
    listed = list_asset(
        seller,
        settlement,
        listing_id="listing-part",
        agent_identity=AGENT,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=PRICE,
        categories=categories,
    )
    settlement.buy("listing-part", buyer=BUYER.address, amount=PRICE)
    import_package(
        listed.export.package,
        buyer,
        committed_root=listed.committed_root,
        expected_signer=SELLER.address,
    )

    verdict = Evaluator(ARBITER_KEY).evaluate(
        listing_id="listing-part",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    assert verdict.verified


def test_summary_reads_as_a_sentence(evaluator, sale, buyer):
    _, listed = sale
    verdict = evaluator.evaluate(
        listing_id="listing-0417",
        committed_root=listed.committed_root,
        buyer_sink=buyer,
        package=listed.export.package,
        expected_signer=SELLER.address,
    )

    assert verdict.summary().startswith("Independently verified")
