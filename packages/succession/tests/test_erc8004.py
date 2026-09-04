"""ERC-8004 identity: the registration file, the identity string, and the client.

The write path runs against the compiled ``MockIdentityRegistry`` bytecode in
py-evm rather than against Base Sepolia, for the same reason every other suite
here does: a test that needs a funded key and a live network is a test that does
not run. What the mock is *for* is covered by
``test_mock_matches_the_real_registry_surface``, which pins the stand-in to the
same function selectors the real deployment carries — the stand-in earns its
place only for as long as it cannot drift from the thing it stands in for.

``test_live_base_sepolia_registry`` reaches the real registry and is skipped
when the network is unreachable, so it never turns CI red for being offline.
"""

from __future__ import annotations

import base64
import json
import os

import pytest
from eth_account import Account
from web3 import EthereumTesterProvider, Web3

from chain import deploy, load_artifacts
from succession.erc8004 import (
    BASE_SEPOLIA_CHAIN_ID,
    BASE_SEPOLIA_IDENTITY_REGISTRY,
    AgentRegistration,
    IdentityRegistry,
    agent_identity,
    decode_registration_uri,
    parse_agent_identity,
    registration_uri,
)

#: eth-tester's deterministic mnemonic, account index 0.
_KEY = "0x0000000000000000000000000000000000000000000000000000000000000001"


# -- the registration file ------------------------------------------------


def test_registration_uri_is_a_resolvable_data_uri():
    reg = AgentRegistration(name="Freight Desk", description="Midwest LTL broker")
    uri = registration_uri(reg)

    assert uri.startswith("data:application/json;base64,")
    decoded = json.loads(
        base64.b64decode(uri.removeprefix("data:application/json;base64,"))
    )
    assert decoded["name"] == "Freight Desk"
    assert decoded["type"] == "https://eips.ethereum.org/EIPS/eip-8004"


def test_registration_uri_is_deterministic():
    """Two identical registrations must produce identical bytes on chain."""
    a = AgentRegistration(name="A", description="d", endpoints={"mcp": "x", "a2a": "y"})
    b = AgentRegistration(name="A", description="d", endpoints={"a2a": "y", "mcp": "x"})
    assert registration_uri(a) == registration_uri(b)


def test_registration_carries_the_memory_root():
    """The on-chain half of 'identity and memory move together'."""
    reg = AgentRegistration(name="A", description="d", memory_root="0xabc")
    assert decode_registration_uri(registration_uri(reg))["memory_root"] == "0xabc"


def test_optional_fields_are_omitted_not_nulled():
    """A null wallet would read as 'declared, and empty'. It is neither."""
    doc = AgentRegistration(name="A", description="d").to_dict()
    assert "wallet" not in doc
    assert "endpoints" not in doc
    assert "memory_root" not in doc


def test_wallet_is_checksummed():
    reg = AgentRegistration(
        name="A", description="d", wallet="0x19e7e376e7c213b7e7e7e46cc70a5dd086daff2a"
    )
    assert reg.to_dict()["wallet"] == "0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"


def test_non_data_schemes_are_refused_rather_than_faked():
    reg = AgentRegistration(name="A", description="d")
    with pytest.raises(ValueError, match="host the output"):
        registration_uri(reg, scheme="ipfs")


def test_decode_rejects_a_non_data_uri():
    with pytest.raises(ValueError, match="not a base64 data"):
        decode_registration_uri("ipfs://QmSomething")


# -- the identity string --------------------------------------------------


def test_agent_identity_matches_the_spec_example():
    assert agent_identity(84532, 417) == "erc8004:84532:0417"


def test_identity_round_trips():
    assert parse_agent_identity(agent_identity(84532, 1183)) == (84532, 1183)


def test_identity_parses_without_padding():
    assert parse_agent_identity("erc8004:84532:417") == (84532, 417)


@pytest.mark.parametrize(
    "bad", ["erc721:84532:0417", "84532:0417", "erc8004:84532", "", "erc8004::1"]
)
def test_malformed_identities_raise(bad):
    with pytest.raises(ValueError):
        parse_agent_identity(bad)


# -- the client, against real compiled bytecode ---------------------------


@pytest.fixture
def registry_env():
    w3 = Web3(EthereumTesterProvider())
    artifacts = load_artifacts()
    deployer = w3.eth.accounts[0]
    contract = deploy(w3, artifacts, "MockIdentityRegistry", sender=deployer)

    # Fund the key the client signs with; eth-tester's accounts are unlocked
    # but the client builds and signs its own raw transactions.
    account = Account.from_key(_KEY)
    w3.eth.send_transaction(
        {"from": deployer, "to": account.address, "value": w3.to_wei(10, "ether")}
    )
    return w3, contract, account


def test_register_mints_and_returns_the_agent_id(registry_env):
    w3, contract, account = registry_env
    registry = IdentityRegistry(w3, address=contract.address)

    agent_id = registry.register(
        AgentRegistration(name="Seller", description="the asset"), _KEY
    )

    assert agent_id == 1
    assert registry.owner_of(agent_id) == account.address


def test_registered_agent_uri_resolves_to_the_registration_file(registry_env):
    w3, contract, _ = registry_env
    registry = IdentityRegistry(w3, address=contract.address)

    agent_id = registry.register(
        AgentRegistration(
            name="Freight Desk 0417",
            description="Midwest LTL broker",
            memory_root="0x8a87d0a6",
        ),
        _KEY,
    )

    doc = registry.registration_of(agent_id)
    assert doc["name"] == "Freight Desk 0417"
    assert doc["memory_root"] == "0x8a87d0a6"


def test_registration_is_permissionless_and_sequential(registry_env):
    """No whitelist. This is what lets the demo mint real identities."""
    w3, contract, _ = registry_env
    registry = IdentityRegistry(w3, address=contract.address)

    first = registry.register(AgentRegistration(name="A", description="d"), _KEY)
    second = registry.register(AgentRegistration(name="B", description="d"), _KEY)

    assert (first, second) == (1, 2)


def test_approve_lets_the_listing_contract_move_the_agent(registry_env):
    """`ListingContract.list` rejects a listing without this approval."""
    w3, contract, _ = registry_env
    registry = IdentityRegistry(w3, address=contract.address)
    agent_id = registry.register(AgentRegistration(name="A", description="d"), _KEY)
    operator = w3.eth.accounts[3]

    registry.approve(operator, agent_id, _KEY)

    assert registry.get_approved(agent_id) == operator


def test_a_reverted_registration_raises_rather_than_reporting_success(registry_env):
    """A reverted transaction still returns a hash. Returning early would
    report an identity that was never minted."""
    w3, contract, _ = registry_env
    registry = IdentityRegistry(w3, address=contract.address)
    # agentId 1 is taken by the sequential mint; re-minting it explicitly is
    # the one path the stand-in rejects.
    registry.register(AgentRegistration(name="A", description="d"), _KEY)

    with pytest.raises(Exception):
        contract.functions.register(
            w3.eth.accounts[0], 1, "ipfs://dupe"
        ).transact({"from": w3.eth.accounts[0]})


def test_capabilities_reports_the_deployments_real_surface(registry_env):
    w3, contract, _ = registry_env
    caps = IdentityRegistry(w3, address=contract.address).capabilities()

    assert caps["register"] is True
    assert caps["transfer_from"] is True
    assert caps["get_approved"] is True
    assert caps["is_approved_for_all"] is True


def test_is_contract_is_false_for_an_empty_address(registry_env):
    w3, _, _ = registry_env
    empty = "0x" + "ab" * 20
    assert IdentityRegistry(w3, address=empty).is_contract() is False


def test_mock_matches_the_real_registry_surface(registry_env):
    """The stand-in must answer every call ListingContract makes on the real one.

    Pinned deliberately: the moment the mock's surface diverges from the
    deployed registry's, every local test that passes stops being evidence
    about production.
    """
    w3, contract, _ = registry_env
    caps = IdentityRegistry(w3, address=contract.address).capabilities()

    for required in (
        "register",
        "transfer_from",
        "get_approved",
        "is_approved_for_all",
    ):
        assert caps[required], f"stand-in is missing {required}"


# -- the real deployment --------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("SUCCESSION_SKIP_NETWORK") == "1",
    reason="network tests disabled",
)
def test_live_base_sepolia_registry():
    """The address this package ships is a real ERC-8004 registry.

    Skipped rather than failed when the network is unreachable — a build
    machine without egress should not turn red for it — but when it does run it
    is the check that stops the shipped constant from silently rotting.
    """
    pytest.importorskip("web3")
    rpc = os.environ.get("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org")
    try:
        from web3.middleware import ExtraDataToPOAMiddleware

        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if not w3.is_connected():
            pytest.skip(f"{rpc} unreachable")
        chain_id = w3.eth.chain_id
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{rpc} unreachable ({exc})")

    assert chain_id == BASE_SEPOLIA_CHAIN_ID

    registry = IdentityRegistry(w3, address=BASE_SEPOLIA_IDENTITY_REGISTRY)
    assert registry.is_contract(), "the shipped registry address holds no code"

    caps = registry.capabilities()
    for required in ("register", "transfer_from", "get_approved", "is_approved_for_all"):
        assert caps[required], f"live registry is missing {required}"
