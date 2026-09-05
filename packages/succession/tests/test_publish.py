"""A real seller listing their own memory, end to end, against real bytecode.

Nothing here is seeded by the marketplace: the store is built record by record
the way a user's agent would fill it, and every figure the listing carries — the
root, the counts, the valuation — is computed from that store. If this suite
passes, a user with their own Sibyl file and their own key can do the same thing
against Base Sepolia, because it is the same code path with a different provider.
"""

from __future__ import annotations

import pytest

pytest.importorskip("web3")
pytest.importorskip("eth_tester")

from eth_account import Account  # noqa: E402

from succession.chain import ChainSettlement  # noqa: E402
from succession.fulfil import release_for  # noqa: E402
from succession.publish import (  # noqa: E402
    PublishError,
    SellerVault,
    listing_id_for,
    publish_listing,
    recover_seller_auth,
    seller_auth_header,
)
from succession.envelope import open_envelope  # noqa: E402
from succession.redaction import Sensitivity, mark  # noqa: E402
from succession.settlement import ListingState  # noqa: E402

from chain import deploy, load_artifacts  # noqa: E402

AGENT_ID = 417
AGENT = f"erc8004:84532:{AGENT_ID}"
PRICE = 25_000_000  # 25 USDC


def _fill(memory, *, counterparties=3):
    """Populate a store the way an agent actually would — not from a catalog."""
    client = memory.client
    client.set_entity(
        "identity",
        AGENT,
        mark(
            {"name": "A real operator", "role": "Logistics agent", "erc8004": AGENT},
            sensitivity=Sensitivity.PUBLIC,
        ),
    )
    for i in range(counterparties):
        client.set_entity(
            "relationship",
            f"counterparty-{i}",
            mark(
                {"company": f"Counterparty {i}", "terms": "net 30"},
                sensitivity=Sensitivity.PRIVATE,
            ),
        )
        client.write_event(
            evaluated={"counterparty": f"counterparty-{i}"},
            acted={"quoted": 2000 + i},
        )
    client.set_state("working", {"open_quote": "q-1"})
    return memory


@pytest.fixture
def chain_env(tmp_path):
    """A deployed ListingContract on an in-process EVM, with a funded buyer."""
    from web3 import EthereumTesterProvider, Web3

    w3 = Web3(EthereumTesterProvider())
    artifacts = load_artifacts()
    funder = w3.eth.accounts[0]

    # A seller and a buyer whose keys this process holds, funded from the
    # tester's own account. They are not tester-managed accounts: every
    # transaction they send is signed locally and pushed as raw, which is
    # exactly what a real user's wallet does and what `ChainSettlement` is for.
    seller_account, buyer_account = Account.create(), Account.create()
    for who in (seller_account.address, buyer_account.address):
        w3.eth.send_transaction(
            {"from": funder, "to": who, "value": w3.to_wei(10, "ether")}
        )

    token = deploy(w3, artifacts, "MockERC20", sender=funder)
    registry = deploy(w3, artifacts, "MockIdentityRegistry", sender=funder)
    listings = deploy(
        w3, artifacts, "ListingContract",
        token.address, registry.address, funder, sender=funder,
    )
    registry.functions.register(seller_account.address, AGENT_ID, "ipfs://x").transact(
        {"from": funder}
    )
    token.functions.mint(buyer_account.address, PRICE * 4).transact({"from": funder})

    seller_key = seller_account.key.hex()
    buyer_key = buyer_account.key.hex()
    backend = ChainSettlement(
        w3, contract_address=listings.address,
        seller_key=seller_key, buyer_key=buyer_key,
    )
    backend.approve_identity(registry.address, seller_account.address, AGENT_ID)
    backend.approve_payment(token.address, buyer_account.address, PRICE * 4)

    return {
        "w3": w3,
        "backend": backend,
        "seller_key": seller_key,
        "seller": seller_account.address,
        "buyer": buyer_account.address,
        "listings": listings,
        "record": {"chain_id": w3.eth.chain_id, "listing_contract": listings.address},
    }


def test_a_seller_lists_their_own_memory_on_chain(chain_env, seller, tmp_path):
    """The headline path: a user's own store becomes a live on-chain listing."""
    _fill(seller)
    vault = SellerVault(tmp_path / "vault")

    stored, asset = publish_listing(
        seller,
        chain_env["backend"],
        agent_identity=AGENT,
        private_key=chain_env["seller_key"],
        price=PRICE,
        chain_id=chain_env["record"]["chain_id"],
        listing_contract=chain_env["record"]["listing_contract"],
        vault=vault,
    )

    # The contract, not the service, is the source of truth.
    on_chain = chain_env["backend"].get(stored.listing_id)
    assert on_chain.state is ListingState.OPEN
    assert on_chain.hash_commitment.lower() == stored.committed_root.lower()
    assert on_chain.seller == chain_env["seller"]
    assert on_chain.price == PRICE

    # And the figures came out of the store rather than out of a fixture.
    assert sum(stored.preview["counts"].values()) > 0
    assert stored.preview["memory_size_bytes"] > 0
    assert stored.valuation_reference


def test_the_listing_id_is_derived_from_what_is_being_sold(chain_env, seller, tmp_path):
    _fill(seller)
    vault = SellerVault(tmp_path / "vault")
    stored, asset = publish_listing(
        seller, chain_env["backend"], agent_identity=AGENT,
        private_key=chain_env["seller_key"], price=PRICE,
        chain_id=1, listing_contract=chain_env["record"]["listing_contract"], vault=vault,
    )
    assert stored.listing_id == listing_id_for(AGENT, stored.committed_root)


def test_relisting_unchanged_memory_is_refused(chain_env, seller, tmp_path):
    """Same memory, same id — the seller is told, not given a second listing."""
    _fill(seller)
    vault = SellerVault(tmp_path / "vault")
    kw = dict(
        agent_identity=AGENT, private_key=chain_env["seller_key"], price=PRICE,
        chain_id=1, listing_contract=chain_env["record"]["listing_contract"], vault=vault,
    )
    publish_listing(seller, chain_env["backend"], **kw)
    with pytest.raises(PublishError, match="already listed"):
        publish_listing(seller, chain_env["backend"], **kw)


def test_the_key_is_not_released_before_escrow(chain_env, seller, tmp_path):
    _fill(seller)
    vault = SellerVault(tmp_path / "vault")
    stored, _ = publish_listing(
        seller, chain_env["backend"], agent_identity=AGENT,
        private_key=chain_env["seller_key"], price=PRICE, chain_id=1,
        listing_contract=chain_env["record"]["listing_contract"], vault=vault,
    )
    handed_over = []
    outcome = release_for(
        stored.listing_id, chain_env["backend"], vault=vault,
        deliver=lambda s, k, b: handed_over.append(k),
    )
    assert outcome.released is False
    assert "no buyer" in outcome.reason
    assert handed_over == []


def test_the_key_is_released_once_escrow_is_funded(chain_env, seller, tmp_path):
    """And what it decrypts is the package that was committed to."""
    _fill(seller)
    vault = SellerVault(tmp_path / "vault")
    stored, asset = publish_listing(
        seller, chain_env["backend"], agent_identity=AGENT,
        private_key=chain_env["seller_key"], price=PRICE, chain_id=1,
        listing_contract=chain_env["record"]["listing_contract"], vault=vault,
    )

    chain_env["backend"].buy(
        stored.listing_id, buyer=chain_env["buyer"], amount=PRICE
    )

    handed_over = {}
    outcome = release_for(
        stored.listing_id, chain_env["backend"], vault=vault,
        deliver=lambda s, k, b: handed_over.update({"key": k, "buyer": b}),
    )
    assert outcome.released is True
    assert handed_over["buyer"] == chain_env["buyer"]

    # The released key opens the envelope, and the package inside re-hashes to
    # the root the contract has been holding since before a buyer existed.
    package = open_envelope(vault.envelope(stored.listing_id), handed_over["key"])
    assert package.integrity["root"].lower() == stored.committed_root.lower()


def test_seller_auth_recovers_the_listing_owner(chain_env):
    key = chain_env["seller_key"]
    headers = seller_auth_header(key, "listing-abc")
    recovered = recover_seller_auth("listing-abc", headers["X-Succession-Signature"])
    assert recovered == chain_env["seller"]


def test_seller_auth_does_not_transfer_between_listings(chain_env):
    """A signature for one listing must not authenticate another."""
    headers = seller_auth_header(chain_env["seller_key"], "listing-abc")
    other = recover_seller_auth("listing-xyz", headers["X-Succession-Signature"])
    assert other != chain_env["seller"]
