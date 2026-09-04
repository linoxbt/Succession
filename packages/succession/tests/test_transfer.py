"""The whole workflow, end to end, including both failure paths."""

from __future__ import annotations

import copy

import pytest
from eth_utils import to_checksum_address

from succession.demokeys import BUYER, SELLER
from succession.envelope import EnvelopeError, open_envelope, seal_package
from succession.seal import SealRegistry, TenantSealed, guard
from succession.settlement import ListingState, LocalSettlement, SettlementError
from succession.transfer import execute_transfer, list_asset

LISTING = "listing-0417"
PRICE = 420_000_000  # 420 USDC, 6 decimals


@pytest.fixture
def settlement(tmp_path):
    return LocalSettlement(tmp_path / "settlement.db")


@pytest.fixture
def seals(tmp_path):
    return SealRegistry(tmp_path / "seals.db")


@pytest.fixture
def listed(seller, settlement, agent_id):
    return list_asset(
        seller,
        settlement,
        listing_id=LISTING,
        agent_identity=agent_id,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=PRICE,
    )


def _run(listed, settlement, seals, seller, buyer, *, envelope=None):
    return execute_transfer(
        listing_id=LISTING,
        settlement=settlement,
        seals=seals,
        envelope=envelope or listed.envelope,
        content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id,
        buyer_sink=buyer,
        buyer_identity=BUYER.agent_id,
        buyer_address=BUYER.address,
        expected_signer=SELLER.address,
    )


# -- the happy path -------------------------------------------------------


def test_full_transfer(listed, settlement, seals, seller, buyer):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    outcome = _run(listed, settlement, seals, seller, buyer)

    assert outcome.verified
    assert outcome.committed_root == outcome.delivered_root
    assert outcome.receipt.outcome == "released"
    assert outcome.receipt.amount == PRICE
    assert outcome.receipt.paid_to == SELLER.address
    assert outcome.receipt.identity_transferred_to == BUYER.address

    listing = settlement.get(LISTING)
    assert listing.state is ListingState.CONFIRMED
    assert listing.sealed is True
    assert listing.escrow_balance == 0


def test_the_certificate_reports_what_actually_happened(listed, settlement, seals, seller, buyer):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    outcome = _run(listed, settlement, seals, seller, buyer)
    cert = outcome.certificate

    assert cert.status == "VERIFIED"
    assert cert.origin_agent == listed.export.package.header["agent_identity"]
    assert cert.successor_agent == BUYER.agent_id
    assert cert.integrity_hash == listed.committed_root
    assert cert.records_transferred == listed.export.record_count
    assert cert.seller_tenant_sealed_at
    assert "SUCCESSION CERTIFICATE" in cert.to_text()
    assert cert.to_json()


def test_the_seller_is_sealed_and_the_buyer_is_not(listed, settlement, seals, seller, buyer):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    _run(listed, settlement, seals, seller, buyer)

    sealed_seller = guard(seller, seals)
    with pytest.raises(TenantSealed):
        sealed_seller.client.set_entity("commitment", "new-quote", {"rate": 1})

    live_buyer = guard(buyer, seals)
    live_buyer.client.set_entity("commitment", "new-quote", {"rate": 1})


def test_the_post_sale_record_lands_in_the_buyers_memory(listed, settlement, seals, seller, buyer):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    outcome = _run(listed, settlement, seals, seller, buyer)

    acquisition = buyer.client.get_entity("provenance", "acquisition")["body"]
    assert acquisition["acquired_from"] == listed.export.package.header["agent_identity"]
    assert acquisition["acquired_by"] == BUYER.agent_id
    assert acquisition["verified_hash"] == outcome.committed_root
    assert len(acquisition["provenance_chain"]) == 1

    lines = [
        line
        for event in buyer.events()
        for line in (event.get("acted") or [])
        if "acquired from" in line
    ]
    assert len(lines) == 1


def test_a_resale_extends_the_provenance_chain(listed, settlement, seals, seller, buyer, tmp_path):
    """Lineage accumulates through the buyer's own memory, with no separate store."""
    from succession.export import export_tenant
    from succession.memory.sibyl import open_tenant

    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    _run(listed, settlement, seals, seller, buyer)

    acquisition = buyer.client.get_entity("provenance", "acquisition")["body"]
    resale = export_tenant(
        buyer,
        agent_identity=BUYER.agent_id,
        private_key=BUYER.private_key,
        provenance_chain=acquisition["provenance_chain"],
    )

    chain = resale.package.header["provenance_chain"]
    assert len(chain) == 1
    assert chain[0]["owner"] == BUYER.agent_id
    assert chain[0]["verified_hash"] == listed.committed_root


# -- the refund path ------------------------------------------------------


def test_a_tampered_envelope_refunds_and_leaves_nothing_behind(
    listed, settlement, seals, seller, buyer
):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)

    tampered = copy.deepcopy(listed.export.package)
    tampered.data["preferences"][0]["body"]["floor_pct"] = 0
    bad_envelope, _ = seal_package(
        tampered,
        listing_id=LISTING,
        hash_commitment=listed.committed_root,
        key=listed.content_key,
    )

    outcome = _run(listed, settlement, seals, seller, buyer, envelope=bad_envelope)

    assert outcome.outcome == "refunded"
    assert outcome.receipt.outcome == "refunded"
    assert outcome.receipt.paid_to == BUYER.address
    assert settlement.get(LISTING).state is ListingState.REFUNDED
    assert buyer.is_empty(), "a failed transfer must not leave the buyer half-written"
    assert not seals.is_sealed(seller.tenant_id), "a failed sale must not seal the seller"


def test_the_seller_keeps_operating_after_a_failed_sale(
    listed, settlement, seals, seller, buyer
):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    tampered = copy.deepcopy(listed.export.package)
    tampered.data["history"].pop()
    bad_envelope, _ = seal_package(
        tampered,
        listing_id=LISTING,
        hash_commitment=listed.committed_root,
        key=listed.content_key,
    )
    _run(listed, settlement, seals, seller, buyer, envelope=bad_envelope)

    guard(seller, seals).client.set_entity("commitment", "still-trading", {"rate": 1})


# -- escrow gating --------------------------------------------------------


def test_the_content_key_is_useless_before_escrow(listed, settlement, seals, seller, buyer):
    """No escrow, no delivery — the transfer refuses to run at all."""
    with pytest.raises(SettlementError, match="funded escrow"):
        _run(listed, settlement, seals, seller, buyer)
    assert buyer.is_empty()


def test_escrow_must_be_exactly_the_asking_price(listed, settlement):
    with pytest.raises(SettlementError, match="exactly the asking price"):
        settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE - 1)


def test_a_listing_cannot_be_bought_twice(listed, settlement):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    with pytest.raises(SettlementError, match="not open"):
        settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)


def test_a_seller_cannot_buy_their_own_listing(listed, settlement):
    with pytest.raises(SettlementError, match="own listing"):
        settlement.buy(LISTING, buyer=SELLER.address, amount=PRICE)


def test_a_race_for_one_listing_does_not_report_two_winners(listed, settlement):
    """The loser of a concurrent buy is told so, rather than handed the winner's row.

    ``buy`` guards its UPDATE on the OPEN state, but until it checked
    ``rowcount`` a losing writer fell through to a read that returned the
    listing as the *other* buyer had left it — a success response for a purchase
    that never happened. Simulated here by taking the listing between the check
    and the write, which is exactly the window a second process occupies.
    """
    other = "0x000000000000000000000000000000000000b0b2"
    real_get = settlement.get
    taken = {"done": False}

    def get_then_take(listing_id):
        row = real_get(listing_id)
        if not taken["done"]:
            taken["done"] = True
            real_buy_conn = settlement._conn
            with real_buy_conn() as conn:
                conn.execute(
                    "UPDATE listings SET state='escrowed', buyer=?, escrow_balance=? "
                    "WHERE listing_id=?",
                    (to_checksum_address(other), PRICE, listing_id),
                )
        return row

    settlement.get = get_then_take
    try:
        with pytest.raises(SettlementError, match="taken during the purchase"):
            settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    finally:
        settlement.get = real_get

    # And the listing still belongs to whoever actually got there first.
    assert settlement.get(LISTING).buyer == to_checksum_address(other)


def test_cancel_withdraws_an_unfunded_listing(listed, settlement):
    assert settlement.get(LISTING).state is ListingState.OPEN
    settlement.cancel(LISTING, seller=SELLER.address)
    assert settlement.get(LISTING).state is ListingState.REFUNDED


def test_only_the_seller_may_cancel(listed, settlement):
    with pytest.raises(SettlementError, match="only the seller"):
        settlement.cancel(LISTING, seller=BUYER.address)


def test_a_funded_listing_cannot_be_cancelled(listed, settlement):
    """Once the buyer's money is in, abandoning the sale is a refund, not a cancel."""
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    with pytest.raises(SettlementError, match="not open"):
        settlement.cancel(LISTING, seller=SELLER.address)


def test_settlement_cannot_be_confirmed_twice(listed, settlement, seals, seller, buyer):
    settlement.buy(LISTING, buyer=BUYER.address, amount=PRICE)
    _run(listed, settlement, seals, seller, buyer)

    with pytest.raises(SettlementError, match="nothing is escrowed"):
        settlement.confirm_transfer(
            LISTING, delivered_hash=listed.committed_root, buyer_identity=BUYER.agent_id
        )


# -- the envelope ---------------------------------------------------------


def test_an_envelope_will_not_open_under_another_listing(listed):
    """The listing is bound in as AAD, so a package cannot be redirected."""
    rewrapped = type(listed.envelope)(
        listing_id="listing-other",
        hash_commitment=listed.envelope.hash_commitment,
        nonce=listed.envelope.nonce,
        ciphertext=listed.envelope.ciphertext,
        tag=listed.envelope.tag,
    )
    with pytest.raises(EnvelopeError):
        open_envelope(rewrapped, listed.content_key)


def test_an_envelope_will_not_open_under_the_wrong_key(listed):
    with pytest.raises(EnvelopeError):
        open_envelope(listed.envelope, b"\x00" * 32)


def test_a_modified_ciphertext_is_rejected(listed):
    flipped = bytearray(listed.envelope.ciphertext)
    flipped[0] ^= 0xFF
    tampered = type(listed.envelope)(
        listing_id=listed.envelope.listing_id,
        hash_commitment=listed.envelope.hash_commitment,
        nonce=listed.envelope.nonce,
        ciphertext=bytes(flipped),
        tag=listed.envelope.tag,
    )
    with pytest.raises(EnvelopeError):
        open_envelope(tampered, listed.content_key)


def test_the_envelope_round_trips(listed):
    from succession.envelope import SealedEnvelope
    from succession.merkle import to_hex

    reopened = open_envelope(
        SealedEnvelope.from_dict(listed.envelope.to_dict()), listed.content_key
    )
    assert to_hex(reopened.tree().root) == listed.committed_root
    assert reopened.header == listed.export.package.header
