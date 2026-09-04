"""ListingContract, executed as real EVM bytecode.

Every guard in ``LocalSettlement`` has a counterpart here. Where the two
disagree, the Solidity is the authority — the Python mirror exists so the
transfer pipeline can be exercised without a funded wallet, not so it can be a
more forgiving contract than the one that ships.
"""

from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import EthereumTesterProvider, Web3
from web3.logs import DISCARD
from chain import deploy, load_artifacts, reverts_with

AGENT_ID = 417
PRICE = 420_000_000
COMMITMENT = bytes.fromhex("9f3a1c8e" + "00" * 24 + "c21edb04")
WRONG = bytes.fromhex("de" * 32)
AGENT_URI = "ipfs://meridian-logistics/registration.json"

# eth-tester's deterministic default mnemonic; index 0..9 map to w3.eth.accounts.
_TESTER_KEYS = None


@pytest.fixture
def chain():
    provider = EthereumTesterProvider()
    w3 = Web3(provider)
    return w3, provider.ethereum_tester


@pytest.fixture
def env(chain):
    w3, tester = chain
    artifacts = load_artifacts()
    deployer, seller, buyer, arbiter, stranger = w3.eth.accounts[:5]

    token = deploy(w3, artifacts, "MockERC20", sender=deployer)
    registry = deploy(w3, artifacts, "MockIdentityRegistry", sender=deployer)
    listings = deploy(
        w3,
        artifacts,
        "ListingContract",
        token.address,
        registry.address,
        arbiter,
        sender=deployer,
    )

    registry.functions.register(seller, AGENT_ID, AGENT_URI).transact({"from": deployer})
    registry.functions.approve(listings.address, AGENT_ID).transact({"from": seller})
    token.functions.mint(buyer, PRICE * 4).transact({"from": deployer})
    token.functions.approve(listings.address, PRICE * 4).transact({"from": buyer})

    return {
        "w3": w3,
        "tester": tester,
        "artifacts": artifacts,
        "token": token,
        "registry": registry,
        "listings": listings,
        "deployer": deployer,
        "seller": seller,
        "buyer": buyer,
        "arbiter": arbiter,
        "stranger": stranger,
    }


def _key_for(tester, address: str) -> str:
    """eth-tester exposes the private key behind each generated account."""
    for account in tester.backend.account_keys:
        if account.public_key.to_checksum_address().lower() == address.lower():
            return account.to_hex()
    raise KeyError(address)


def attest(env, listing_id: bytes, commitment: bytes, *, signer: str | None = None) -> bytes:
    """Sign the listing attestation the contract will recover."""
    digest = env["listings"].functions.attestationDigest(
        listing_id, AGENT_ID, commitment
    ).call()
    key = _key_for(env["tester"], signer or env["seller"])
    return Account.sign_message(encode_defunct(digest), key).signature


def make_listing(env, listing_id=b"L" + b"\x00" * 31, commitment=COMMITMENT, price=PRICE):
    env["listings"].functions.list(
        listing_id, AGENT_ID, commitment, price, attest(env, listing_id, commitment)
    ).transact({"from": env["seller"]})
    return listing_id


# -- listing --------------------------------------------------------------


def test_a_listing_records_the_commitment(env):
    listing_id = make_listing(env)
    listing = env["listings"].functions.getListing(listing_id).call()

    assert listing[0] == env["seller"]
    assert listing[2] == AGENT_ID
    assert listing[3] == COMMITMENT
    assert listing[4] == PRICE
    assert listing[6] == 1  # State.Open


def test_a_non_owner_cannot_list_the_agent(env):
    listing_id = b"X" + b"\x00" * 31
    with reverts_with(env["listings"], "NotAgentOwner"):
        env["listings"].functions.list(
            listing_id, AGENT_ID, COMMITMENT, PRICE, attest(env, listing_id, COMMITMENT, signer=env["stranger"])
        ).transact({"from": env["stranger"]})


def test_listing_requires_registry_approval(env):
    """A listing that cannot move its identity must never reach the market."""
    env["registry"].functions.approve(
        "0x0000000000000000000000000000000000000000", AGENT_ID
    ).transact({"from": env["seller"]})

    listing_id = b"Y" + b"\x00" * 31
    with reverts_with(env["listings"], "RegistryNotApproved"):
        env["listings"].functions.list(
            listing_id, AGENT_ID, COMMITMENT, PRICE, attest(env, listing_id, COMMITMENT)
        ).transact({"from": env["seller"]})


def test_an_attestation_from_the_wrong_key_is_rejected(env):
    listing_id = b"Z" + b"\x00" * 31
    with reverts_with(env["listings"], "BadAttestation"):
        env["listings"].functions.list(
            listing_id, AGENT_ID, COMMITMENT, PRICE,
            attest(env, listing_id, COMMITMENT, signer=env["stranger"]),
        ).transact({"from": env["seller"]})


def test_an_attestation_cannot_be_replayed_onto_another_listing(env):
    """The digest binds the listing id, so a signature does not travel.

    The first listing is cancelled so the agent is free again. Without that the
    one-live-listing-per-agent guard rejects the second listing before the
    attestation is ever recovered, and this test would pass for the wrong reason.
    """
    first = make_listing(env)
    stolen = attest(env, first, COMMITMENT)
    env["listings"].functions.cancel(first).transact({"from": env["seller"]})

    second = b"B" + b"\x00" * 31
    with reverts_with(env["listings"], "BadAttestation"):
        env["listings"].functions.list(
            second, AGENT_ID, COMMITMENT, PRICE, stolen
        ).transact({"from": env["seller"]})


def test_an_agent_cannot_be_listed_twice_at_once(env):
    """Two live listings for one agent would strand the second buyer's escrow."""
    make_listing(env)
    second = b"D" + b"\x00" * 31
    with reverts_with(env["listings"], "AgentAlreadyListed"):
        env["listings"].functions.list(
            second, AGENT_ID, COMMITMENT, PRICE, attest(env, second, COMMITMENT)
        ).transact({"from": env["seller"]})


def test_cancel_withdraws_an_unfunded_listing_and_frees_the_agent(env):
    first = make_listing(env)
    env["listings"].functions.cancel(first).transact({"from": env["seller"]})
    assert env["listings"].functions.getListing(first).call()[6] == 4  # Refunded
    assert env["listings"].functions.activeListing(AGENT_ID).call() == b"\x00" * 32

    second = b"E" + b"\x00" * 31
    env["listings"].functions.list(
        second, AGENT_ID, COMMITMENT, PRICE, attest(env, second, COMMITMENT)
    ).transact({"from": env["seller"]})
    assert env["listings"].functions.activeListing(AGENT_ID).call() == second


def test_only_the_seller_may_cancel(env):
    first = make_listing(env)
    with reverts_with(env["listings"], "NotAuthorised"):
        env["listings"].functions.cancel(first).transact({"from": env["stranger"]})


def test_a_settled_agent_cannot_be_confirmed_again(env):
    """The seal is checked at settlement, not only at listing time."""
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["buyer"]}
    )
    assert env["listings"].functions.isSealed(AGENT_ID).call() is True


def test_a_zero_commitment_is_rejected(env):
    listing_id = b"C" + b"\x00" * 31
    zero = b"\x00" * 32
    with reverts_with(env["listings"], "ZeroCommitment"):
        env["listings"].functions.list(
            listing_id, AGENT_ID, zero, PRICE, attest(env, listing_id, zero)
        ).transact({"from": env["seller"]})


def test_a_duplicate_listing_id_is_rejected(env):
    listing_id = make_listing(env)
    with reverts_with(env["listings"], "ListingExists"):
        env["listings"].functions.list(
            listing_id, AGENT_ID, COMMITMENT, PRICE, attest(env, listing_id, COMMITMENT)
        ).transact({"from": env["seller"]})


# -- escrow ---------------------------------------------------------------


def test_buying_moves_funds_into_the_contract(env):
    listing_id = make_listing(env)
    before = env["token"].functions.balanceOf(env["buyer"]).call()

    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    assert env["token"].functions.balanceOf(env["buyer"]).call() == before - PRICE
    assert env["token"].functions.balanceOf(env["listings"].address).call() == PRICE
    assert env["listings"].functions.getListing(listing_id).call()[6] == 2  # Escrowed


def test_the_seller_cannot_buy_their_own_listing(env):
    listing_id = make_listing(env)
    env["token"].functions.mint(env["seller"], PRICE).transact({"from": env["deployer"]})
    env["token"].functions.approve(env["listings"].address, PRICE).transact({"from": env["seller"]})

    with reverts_with(env["listings"], "SelfPurchase"):
        env["listings"].functions.buy(listing_id).transact({"from": env["seller"]})


def test_a_listing_cannot_be_bought_twice(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    with reverts_with(env["listings"], "WrongState"):
        env["listings"].functions.buy(listing_id).transact({"from": env["stranger"]})


# -- settlement -----------------------------------------------------------


def test_a_matching_hash_pays_moves_and_seals_in_one_transaction(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    seller_before = env["token"].functions.balanceOf(env["seller"]).call()

    tx = env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["buyer"]}
    )
    receipt = env["w3"].eth.wait_for_transaction_receipt(tx)

    assert receipt["status"] == 1
    # All three effects, in the one transaction.
    assert env["token"].functions.balanceOf(env["seller"]).call() == seller_before + PRICE
    assert env["registry"].functions.ownerOf(AGENT_ID).call() == env["buyer"]
    assert env["listings"].functions.isSealed(AGENT_ID).call() is True
    assert env["token"].functions.balanceOf(env["listings"].address).call() == 0

    events = env["listings"].events.TransferConfirmed().process_receipt(receipt, errors=DISCARD)
    assert events[0]["args"]["verifiedHash"] == COMMITMENT


def test_the_identity_carries_its_registration_uri(env):
    """Transferring the ERC-721 transfers the identity — URI and all."""
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["buyer"]}
    )
    assert env["registry"].functions.agentURI(AGENT_ID).call() == AGENT_URI


def test_a_mismatched_hash_refunds_instead_of_reverting(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    buyer_before = env["token"].functions.balanceOf(env["buyer"]).call()

    tx = env["listings"].functions.confirmTransfer(listing_id, WRONG).transact(
        {"from": env["buyer"]}
    )
    receipt = env["w3"].eth.wait_for_transaction_receipt(tx)

    assert receipt["status"] == 1
    assert env["token"].functions.balanceOf(env["buyer"]).call() == buyer_before + PRICE
    # Nothing else moved: the seller keeps the agent and is not sealed.
    assert env["registry"].functions.ownerOf(AGENT_ID).call() == env["seller"]
    assert env["listings"].functions.isSealed(AGENT_ID).call() is False
    assert env["listings"].functions.getListing(listing_id).call()[6] == 4  # Refunded

    events = env["listings"].events.Refunded().process_receipt(receipt, errors=DISCARD)
    assert "Hash mismatch" in events[0]["args"]["reason"]


def test_only_the_buyer_or_arbiter_may_confirm(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    with reverts_with(env["listings"], "NotAuthorised"):
        env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
            {"from": env["stranger"]}
        )

    # The seller is not authorised either: confirmation is the buyer's assertion
    # about what they received, and a seller who could make it would be grading
    # their own delivery.
    with reverts_with(env["listings"], "NotAuthorised"):
        env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
            {"from": env["seller"]}
        )


def test_the_arbiter_can_confirm(env):
    """The hook for an Evaluator-style agent that re-derives the root itself."""
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["arbiter"]}
    )
    assert env["registry"].functions.ownerOf(AGENT_ID).call() == env["buyer"]


def test_settlement_cannot_happen_twice(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["buyer"]}
    )

    with reverts_with(env["listings"], "WrongState"):
        env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
            {"from": env["buyer"]}
        )


def test_a_sealed_agent_cannot_be_relisted(env):
    """The seal is what stops the same memory being sold twice."""
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
        {"from": env["buyer"]}
    )

    env["registry"].functions.approve(env["listings"].address, AGENT_ID).transact(
        {"from": env["buyer"]}
    )
    second = b"S" + b"\x00" * 31
    with reverts_with(env["listings"], "AgentAlreadySealed"):
        env["listings"].functions.list(
            second, AGENT_ID, COMMITMENT, PRICE, attest(env, second, COMMITMENT, signer=env["buyer"])
        ).transact({"from": env["buyer"]})


def test_confirming_without_escrow_reverts(env):
    listing_id = make_listing(env)
    with reverts_with(env["listings"], "WrongState"):
        env["listings"].functions.confirmTransfer(listing_id, COMMITMENT).transact(
            {"from": env["buyer"]}
        )


# -- refunds and the expiry window ----------------------------------------


def test_either_party_can_abandon_a_funded_sale(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    before = env["token"].functions.balanceOf(env["buyer"]).call()

    env["listings"].functions.refund(listing_id, "seller withdrew").transact(
        {"from": env["seller"]}
    )
    assert env["token"].functions.balanceOf(env["buyer"]).call() == before + PRICE


def test_a_stranger_cannot_trigger_a_refund(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    with reverts_with(env["listings"], "NotAuthorised"):
        env["listings"].functions.refund(listing_id, "mine now").transact(
            {"from": env["stranger"]}
        )


def test_escrow_cannot_be_reclaimed_before_the_window_elapses(env):
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})

    with reverts_with(env["listings"], "WindowNotElapsed"):
        env["listings"].functions.reclaimExpired(listing_id).transact(
            {"from": env["stranger"]}
        )


def test_abandoned_escrow_is_reclaimable_by_anyone_after_the_window(env):
    """A buyer who funds escrow and vanishes must not lock their own money here."""
    listing_id = make_listing(env)
    env["listings"].functions.buy(listing_id).transact({"from": env["buyer"]})
    before = env["token"].functions.balanceOf(env["buyer"]).call()

    env["tester"].time_travel(env["w3"].eth.get_block("latest")["timestamp"] + 8 * 24 * 3600)

    env["listings"].functions.reclaimExpired(listing_id).transact({"from": env["stranger"]})

    assert env["token"].functions.balanceOf(env["buyer"]).call() == before + PRICE
    assert env["registry"].functions.ownerOf(AGENT_ID).call() == env["seller"]
    assert env["listings"].functions.isSealed(AGENT_ID).call() is False


# -- token behaviour ------------------------------------------------------


def test_a_token_that_returns_false_is_not_treated_as_paid(env, chain):
    """Plenty of real tokens signal failure by returning false. Ignoring the
    return value would emit a success event for a payment that never moved."""
    w3, tester = chain
    artifacts = env["artifacts"]
    deployer, seller, buyer, arbiter = w3.eth.accounts[:4]

    token = deploy(w3, artifacts, "RevertingToken", sender=deployer)
    registry = deploy(w3, artifacts, "MockIdentityRegistry", sender=deployer)
    listings = deploy(
        w3, artifacts, "ListingContract", token.address, registry.address, arbiter, sender=deployer
    )
    registry.functions.register(seller, AGENT_ID, AGENT_URI).transact({"from": deployer})
    registry.functions.approve(listings.address, AGENT_ID).transact({"from": seller})
    token.functions.mint(buyer, PRICE * 2).transact({"from": deployer})
    token.functions.approve(listings.address, PRICE * 2).transact({"from": buyer})

    listing_id = b"F" + b"\x00" * 31
    digest = listings.functions.attestationDigest(listing_id, AGENT_ID, COMMITMENT).call()
    signature = Account.sign_message(
        encode_defunct(digest), _key_for(tester, seller)
    ).signature
    listings.functions.list(listing_id, AGENT_ID, COMMITMENT, PRICE, signature).transact(
        {"from": seller}
    )
    listings.functions.buy(listing_id).transact({"from": buyer})

    token.functions.setFailTransfers(True).transact({"from": deployer})

    with reverts_with(listings, "TransferFailed"):
        listings.functions.confirmTransfer(listing_id, COMMITMENT).transact({"from": buyer})

    # The whole transaction reverted, so nothing moved.
    assert registry.functions.ownerOf(AGENT_ID).call() == seller
    assert listings.functions.isSealed(AGENT_ID).call() is False
