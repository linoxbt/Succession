"""The full transfer, settled against the real contract bytecode.

Base Sepolia is not reachable from CI, so these run ``ListingContract`` in
py-evm through web3's EthereumTesterProvider. That is a genuine EVM executing
the genuine compiled artifact: the escrow, the hash comparison, the ERC-8004
identity transfer, and the seal are all really happening. What is *not* proven
here is anything about Base specifically — gas pricing, RPC behaviour, or
finality. Those need the deployment.

The point of the suite is that ``ChainSettlement`` and ``LocalSettlement`` are
interchangeable behind one interface, so the orchestrator above them cannot
tell which it has.
"""

from __future__ import annotations

import pytest
from eth_account import Account
from web3 import EthereumTesterProvider, Web3

from succession.chain import ChainSettlement, listing_id_to_bytes32
from succession.demokeys import BUYER, SELLER
from succession.seal import SealRegistry
from succession.settlement import ListingState, SettlementError
from succession.transfer import execute_transfer, list_asset

from chain import deploy, load_artifacts

AGENT_TOKEN_ID = 417
PRICE = 420_000_000
LISTING = "listing-0417"
AGENT_URI = "ipfs://meridian-logistics/registration.json"


@pytest.fixture
def evm(tmp_path):
    """A funded chain with the contracts deployed and approvals in place."""
    provider = EthereumTesterProvider()
    w3 = Web3(provider)
    tester = provider.ethereum_tester
    artifacts = load_artifacts()

    funder = w3.eth.accounts[0]
    arbiter = w3.eth.accounts[9]

    # Real keys for our demo identities, funded from the tester's accounts, so
    # the signatures the contract recovers are the same ones the SMP header
    # carries. Reusing a tester account would prove less: the whole point is
    # that the wallet holding the ERC-8004 identity signs both.
    seller = Account.from_key(SELLER.private_key).address
    buyer = Account.from_key(BUYER.private_key).address
    for who in (seller, buyer):
        w3.eth.send_transaction(
            {"from": funder, "to": who, "value": w3.to_wei(10, "ether")}
        )

    token = deploy(w3, artifacts, "MockERC20", sender=funder)
    registry = deploy(w3, artifacts, "MockIdentityRegistry", sender=funder)
    listings = deploy(
        w3, artifacts, "ListingContract",
        token.address, registry.address, arbiter, sender=funder,
    )

    registry.functions.register(seller, AGENT_TOKEN_ID, AGENT_URI).transact(
        {"from": funder}
    )
    token.functions.mint(buyer, PRICE * 10).transact({"from": funder})

    settlement = ChainSettlement(
        w3,
        contract_address=listings.address,
        seller_key=SELLER.private_key,
        buyer_key=BUYER.private_key,
    )
    settlement.approve_identity(registry.address, seller, AGENT_TOKEN_ID)
    settlement.approve_payment(token.address, buyer, PRICE * 10)

    return {
        "w3": w3, "tester": tester, "token": token, "registry": registry,
        "listings": listings, "settlement": settlement,
        "seller": seller, "buyer": buyer, "arbiter": arbiter,
    }


# -- the backend itself ---------------------------------------------------


def test_listing_id_encoding_round_trips():
    from succession.chain import bytes32_to_listing_id

    assert bytes32_to_listing_id(listing_id_to_bytes32(LISTING)) == LISTING


def test_an_overlong_listing_id_is_refused_not_truncated():
    """Two ids differing only past byte 32 would collide on one storage slot."""
    with pytest.raises(SettlementError, match="32"):
        listing_id_to_bytes32("l" * 33)


def test_the_backend_reads_listings_back_off_chain(evm, seller, agent_id):
    from succession.export import export_tenant

    exported = export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key
    )
    listing = evm["settlement"].list_asset(
        listing_id=LISTING,
        agent_id=agent_id,
        seller=evm["seller"],
        seller_signature=exported.package.header["signature"],
        hash_commitment=exported.root_hex,
        price=PRICE,
    )
    assert listing.state is ListingState.OPEN
    assert listing.hash_commitment == exported.root_hex
    assert listing.price == PRICE
    assert listing.agent_id == str(AGENT_TOKEN_ID)


# -- the whole pipeline, settled on chain ---------------------------------


def _list_and_escrow(evm, seller, agent_id, tmp_path):
    listed = list_asset(
        seller,
        evm["settlement"],
        listing_id=LISTING,
        agent_identity=agent_id,
        seller_address=evm["seller"],
        private_key=SELLER.private_key,
        price=PRICE,
    )
    evm["settlement"].buy(LISTING, buyer=evm["buyer"], amount=PRICE)
    return listed


def test_a_full_transfer_settles_on_chain(evm, seller, buyer, agent_id, tmp_path):
    listed = _list_and_escrow(evm, seller, agent_id, tmp_path)
    seller_before = evm["token"].functions.balanceOf(evm["seller"]).call()

    outcome = execute_transfer(
        listing_id=LISTING,
        settlement=evm["settlement"],
        seals=SealRegistry(tmp_path / "seals.db"),
        envelope=listed.envelope,
        content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id,
        buyer_sink=buyer,
        buyer_identity=BUYER.agent_id,
        buyer_address=evm["buyer"],
        expected_signer=SELLER.address,
    )

    assert outcome.verified
    assert outcome.committed_root == outcome.delivered_root
    assert outcome.receipt.outcome == "released"
    assert outcome.receipt.reference.startswith("0x"), "reference must be a real tx hash"

    # The three effects, read off the chain rather than off our own objects.
    assert evm["token"].functions.balanceOf(evm["seller"]).call() == seller_before + PRICE
    assert evm["registry"].functions.ownerOf(AGENT_TOKEN_ID).call() == evm["buyer"]
    assert evm["listings"].functions.isSealed(AGENT_TOKEN_ID).call() is True
    assert evm["settlement"].get(LISTING).state is ListingState.CONFIRMED


def test_the_buyers_agent_recalls_after_an_on_chain_sale(evm, seller, buyer, agent_id, tmp_path):
    listed = _list_and_escrow(evm, seller, agent_id, tmp_path)
    execute_transfer(
        listing_id=LISTING, settlement=evm["settlement"],
        seals=SealRegistry(tmp_path / "seals.db"),
        envelope=listed.envelope, content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
        buyer_identity=BUYER.agent_id, buyer_address=evm["buyer"],
        expected_signer=SELLER.address,
    )
    from succession.agent import Agent

    reply = Agent(buyer).respond("Northwind Mills here about the Duluth run")
    assert reply.recalled
    assert "2,380" in reply.text


def test_the_certificate_carries_the_transaction_hash(evm, seller, buyer, agent_id, tmp_path):
    listed = _list_and_escrow(evm, seller, agent_id, tmp_path)
    outcome = execute_transfer(
        listing_id=LISTING, settlement=evm["settlement"],
        seals=SealRegistry(tmp_path / "seals.db"),
        envelope=listed.envelope, content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
        buyer_identity=BUYER.agent_id, buyer_address=evm["buyer"],
        expected_signer=SELLER.address,
    )
    assert outcome.certificate.settlement_reference == outcome.receipt.reference
    assert outcome.certificate.settlement_reference.startswith("0x")


def test_a_bad_delivery_refunds_on_chain_and_leaves_nothing_behind(
    evm, seller, buyer, agent_id, tmp_path
):
    """The refund path, read from the emitted event rather than assumed."""
    import copy

    from succession.envelope import seal_package

    listed = _list_and_escrow(evm, seller, agent_id, tmp_path)
    buyer_before = evm["token"].functions.balanceOf(evm["buyer"]).call()

    tampered = copy.deepcopy(listed.export.package)
    tampered.data["preferences"][0]["body"]["floor_pct"] = 0
    bad, _ = seal_package(
        tampered, listing_id=LISTING, hash_commitment=listed.committed_root,
        key=listed.content_key,
    )

    outcome = execute_transfer(
        listing_id=LISTING, settlement=evm["settlement"],
        seals=SealRegistry(tmp_path / "seals.db"),
        envelope=bad, content_key=listed.content_key,
        seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
        buyer_identity=BUYER.agent_id, buyer_address=evm["buyer"],
        expected_signer=SELLER.address,
    )

    assert outcome.outcome == "refunded"
    assert evm["token"].functions.balanceOf(evm["buyer"]).call() == buyer_before + PRICE
    assert evm["registry"].functions.ownerOf(AGENT_TOKEN_ID).call() == evm["seller"]
    assert evm["listings"].functions.isSealed(AGENT_TOKEN_ID).call() is False
    assert buyer.is_empty()


def test_the_content_key_is_still_gated_on_escrow(evm, seller, buyer, agent_id, tmp_path):
    listed = list_asset(
        seller, evm["settlement"], listing_id=LISTING, agent_identity=agent_id,
        seller_address=evm["seller"], private_key=SELLER.private_key, price=PRICE,
    )
    with pytest.raises(SettlementError, match="funded escrow"):
        execute_transfer(
            listing_id=LISTING, settlement=evm["settlement"],
            seals=SealRegistry(tmp_path / "seals.db"),
            envelope=listed.envelope, content_key=listed.content_key,
            seller_tenant_id=seller.tenant_id, buyer_sink=buyer,
            buyer_identity=BUYER.agent_id, buyer_address=evm["buyer"],
            expected_signer=SELLER.address,
        )
    assert buyer.is_empty()


def test_escrow_must_be_exactly_the_asking_price(evm, seller, agent_id, tmp_path):
    _list_and_escrow  # noqa: B018 - referenced for symmetry with the local suite
    list_asset(
        seller, evm["settlement"], listing_id=LISTING, agent_identity=agent_id,
        seller_address=evm["seller"], private_key=SELLER.private_key, price=PRICE,
    )
    with pytest.raises(SettlementError, match="exactly the asking price"):
        evm["settlement"].buy(LISTING, buyer=evm["buyer"], amount=PRICE - 1)


def test_a_reverted_transaction_is_not_reported_as_success(evm, seller, agent_id):
    """A transaction that reverts still returns a hash."""
    list_asset(
        seller, evm["settlement"], listing_id=LISTING, agent_identity=agent_id,
        seller_address=evm["seller"], private_key=SELLER.private_key, price=PRICE,
    )
    with pytest.raises(Exception):
        # Confirming before escrow reverts; the backend must surface that.
        evm["settlement"].confirm_transfer(
            LISTING, delivered_hash="0x" + "11" * 32, buyer_identity=BUYER.agent_id
        )


# -- cross-language encoding parity ---------------------------------------


def test_listing_id_encoding_vectors():
    """Pinned vectors, shared with the frontend's `listingIdToBytes32`.

    The browser re-implements this encoding in TypeScript because it builds the
    `confirmTransfer` calldata itself. Two implementations of one wire format
    is a drift risk with an expensive failure mode — a mismatched key does not
    error, it addresses a *different* storage slot, so the contract reports
    `NoSuchListing` for a listing that plainly exists. These vectors are the
    fixed point both sides are checked against; `web/src/chain/Wallet.tsx`
    quotes them in the same order.
    """
    from succession.chain import listing_id_to_bytes32

    vectors = {
        "listing-0417": "6c697374696e672d303431370000000000000000000000000000000000000000",
        "a": "6100000000000000000000000000000000000000000000000000000000000000",
        "listing-with-a-quite-long-id!!": (
            "6c697374696e672d776974682d612d71756974652d6c6f6e672d696421210000"
        ),
    }
    for listing_id, expected in vectors.items():
        assert listing_id_to_bytes32(listing_id).hex() == expected


def test_listing_id_longer_than_32_bytes_is_refused():
    """Truncating would make two distinct listings share one storage slot."""
    from succession.chain import listing_id_to_bytes32
    from succession.settlement import SettlementError

    with pytest.raises(SettlementError, match="the contract key is 32"):
        listing_id_to_bytes32("x" * 33)
