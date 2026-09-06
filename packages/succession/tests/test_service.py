"""The marketplace HTTP layer, against a real deployed contract.

Every test here runs the routes a browser calls, backed by ``ListingContract``
executing in py-evm — the same bytecode that goes to Base Sepolia. There is no
seeded catalogue and no demo tenant, because the service no longer has either:
a listing exists in these tests only because a seller published one from a store
built record by record in the fixture.

What is being defended, specifically:

* the chain is authoritative — metadata cannot describe a sale the contract does
  not have, and a row whose chain read fails is dropped rather than rendered
* only the address the *contract* records as seller can publish or release
* a content key is never accepted or served except against funded escrow
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("web3")
pytest.importorskip("eth_tester")

from eth_account import Account  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from succession.chain import ChainSettlement  # noqa: E402
from succession.publish import SellerVault, publish_listing, seller_auth_header  # noqa: E402
from succession.redaction import Sensitivity, mark  # noqa: E402

from chain import deploy, load_artifacts  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENT_ID = 417
AGENT = f"erc8004:84532:{AGENT_ID}"
PRICE = 25_000_000


def _fill(memory):
    """A store filled the way an agent fills one, not from a catalogue."""
    client = memory.client
    client.set_entity(
        "identity", AGENT,
        mark({"name": "Real Operator", "role": "Freight agent", "erc8004": AGENT},
             sensitivity=Sensitivity.PUBLIC),
    )
    for i in range(3):
        client.set_entity(
            "relationship", f"cp-{i}",
            mark({"company": f"Counterparty {i}"}, sensitivity=Sensitivity.PRIVATE),
        )
        client.write_event(evaluated={"cp": f"cp-{i}"}, acted={"quoted": 2000 + i})
    return memory


@pytest.fixture
def market(tmp_path, monkeypatch, seller):
    """A running marketplace whose chain is a real contract in py-evm."""
    from web3 import EthereumTesterProvider, Web3

    monkeypatch.setenv("SUCCESSION_WORKDIR", str(tmp_path / "state"))
    monkeypatch.setenv("SUCCESSION_VAULT", str(tmp_path / "vault"))
    for module in [m for m in list(sys.modules) if m.startswith("service")]:
        del sys.modules[module]

    w3 = Web3(EthereumTesterProvider())
    artifacts = load_artifacts()
    funder = w3.eth.accounts[0]

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

    backend = ChainSettlement(
        w3, contract_address=listings.address,
        seller_key=seller_account.key.hex(), buyer_key=buyer_account.key.hex(),
    )
    backend.approve_identity(registry.address, seller_account.address, AGENT_ID)
    backend.approve_payment(token.address, buyer_account.address, PRICE * 4)

    record = {
        "chain_id": w3.eth.chain_id,
        "listing_contract": listings.address,
        "payment_token": token.address,
        "identity_registry": registry.address,
    }

    from service import app as app_module

    # The service reads the chain read-only; here that read points at py-evm
    # instead of an RPC. Nothing else about the route code changes.
    app_module.CHAIN_PROVIDER = lambda: (backend, record)
    monkeypatch.setattr(app_module, "_deployment", lambda: record)

    vault = SellerVault(tmp_path / "vault")
    stored, asset = publish_listing(
        _fill(seller), backend, agent_identity=AGENT,
        private_key=seller_account.key.hex(), price=PRICE,
        chain_id=record["chain_id"], listing_contract=listings.address, vault=vault,
    )

    with TestClient(app_module.app) as client:
        yield {
            "client": client,
            "backend": backend,
            "stored": stored,
            "asset": asset,
            "vault": vault,
            "seller_key": seller_account.key.hex(),
            "seller": seller_account.address,
            "buyer": buyer_account.address,
            "buyer_key": buyer_account.key.hex(),
            "record": record,
        }


def _publish(market, **overrides):
    stored = market["stored"]
    body = {
        "listing_id": stored.listing_id,
        "agent_identity": stored.agent_identity,
        "committed_root": stored.committed_root,
        "chain_id": stored.chain_id,
        "contract": stored.listing_contract,
        "name": "Real Operator",
        "vertical": "Freight",
        "valuation": stored.valuation_reference,
        "preview": stored.preview,
        "envelope": market["asset"].envelope.to_dict(),
    }
    body.update(overrides)
    headers = seller_auth_header(market["seller_key"], body["listing_id"])
    return market["client"].post("/api/listings", json=body, headers=headers)


# --- publishing ----------------------------------------------------------


def test_the_marketplace_is_empty_until_a_seller_publishes(market):
    """No seed data. An empty market is the true answer, not a bug."""
    body = market["client"].get("/api/marketplace").json()
    assert body["count"] == 0
    assert body["listings"] == []


def test_a_seller_publishes_and_the_row_comes_from_chain(market):
    assert _publish(market).status_code == 200
    body = market["client"].get("/api/marketplace").json()
    assert body["count"] == 1

    row = body["listings"][0]
    stored = market["stored"]
    # Truth from the contract...
    assert row["listing"]["seller"] == market["seller"]
    assert row["listing"]["hash_commitment"].lower() == stored.committed_root.lower()
    assert row["listing"]["price"] == PRICE
    assert row["listing"]["state"] == "open"
    # ...presentation from the registry, computed off the real store.
    assert row["name"] == "Real Operator"
    assert sum(row["preview"]["counts"].values()) > 0


def test_metadata_cannot_claim_a_commitment_the_contract_does_not_have(market):
    """The join is a check, not a merge."""
    response = _publish(market, committed_root="0x" + "ee" * 32)
    assert response.status_code == 409
    assert "commits" in response.json()["detail"]


def test_a_stranger_cannot_publish_someone_elses_listing(market):
    stranger = Account.create()
    body = {
        "listing_id": market["stored"].listing_id,
        "agent_identity": AGENT,
        "committed_root": market["stored"].committed_root,
        "chain_id": market["stored"].chain_id,
        "contract": market["stored"].listing_contract,
    }
    headers = seller_auth_header(stranger.key.hex(), body["listing_id"])
    response = market["client"].post("/api/listings", json=body, headers=headers)
    assert response.status_code == 403
    assert "is not the seller" in response.json()["detail"]


def test_publishing_without_a_signature_is_refused(market):
    body = {
        "listing_id": market["stored"].listing_id,
        "agent_identity": AGENT,
        "committed_root": market["stored"].committed_root,
        "chain_id": market["stored"].chain_id,
        "contract": market["stored"].listing_contract,
    }
    assert market["client"].post("/api/listings", json=body).status_code == 401


def test_a_listing_that_is_not_on_chain_is_refused(market):
    response = _publish(market, listing_id="listing-never-happened")
    assert response.status_code == 404


# --- the envelope and the key --------------------------------------------


def test_the_envelope_is_public_and_the_key_is_not(market):
    _publish(market)
    listing_id = market["stored"].listing_id

    # Ciphertext is served to anyone: it is inert without the key.
    envelope = market["client"].get(f"/api/listing/{listing_id}/envelope")
    assert envelope.status_code == 200
    assert envelope.json()["ciphertext"]

    # The key is not, because escrow has not been funded.
    key = market["client"].get(f"/api/listing/{listing_id}/key")
    assert key.status_code == 409


def test_a_key_is_not_accepted_before_escrow(market):
    """Even from the real seller. The service checks the chain itself."""
    _publish(market)
    listing_id = market["stored"].listing_id
    response = market["client"].post(
        f"/api/listing/{listing_id}/key",
        json={"content_key": market["asset"].content_key.hex()},
        headers=seller_auth_header(market["seller_key"], listing_id),
    )
    assert response.status_code == 409
    assert "funded escrow" in response.json()["detail"]


def test_the_key_flows_once_escrow_is_funded(market):
    """Seller releases, buyer collects, and what comes back opens the envelope."""
    from succession.envelope import SealedEnvelope, open_envelope

    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)

    released = market["client"].post(
        f"/api/listing/{listing_id}/key",
        json={"content_key": market["asset"].content_key.hex()},
        headers=seller_auth_header(market["seller_key"], listing_id),
    )
    assert released.status_code == 200
    assert released.json()["buyer"] == market["buyer"]

    collected = market["client"].get(f"/api/listing/{listing_id}/key")
    assert collected.status_code == 200

    key = bytes.fromhex(collected.json()["content_key"])
    envelope = SealedEnvelope.from_dict(
        market["client"].get(f"/api/listing/{listing_id}/envelope").json()
    )
    package = open_envelope(envelope, key)
    assert package.integrity["root"].lower() == market["stored"].committed_root.lower()


def test_a_stranger_cannot_release_a_key(market):
    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)
    stranger = Account.create()
    response = market["client"].post(
        f"/api/listing/{listing_id}/key",
        json={"content_key": market["asset"].content_key.hex()},
        headers=seller_auth_header(stranger.key.hex(), listing_id),
    )
    assert response.status_code == 403


def test_a_malformed_key_is_rejected(market):
    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)
    response = market["client"].post(
        f"/api/listing/{listing_id}/key",
        json={"content_key": "not-hex"},
        headers=seller_auth_header(market["seller_key"], listing_id),
    )
    assert response.status_code == 422


# --- listing detail and status -------------------------------------------


def test_listing_detail_joins_chain_and_metadata(market):
    _publish(market)
    body = market["client"].get(f"/api/listing/{market['stored'].listing_id}").json()
    assert body["listing"]["state"] == "open"
    assert body["agent_identity"] == AGENT
    assert body["valuation"]


def test_an_unknown_listing_is_404(market):
    assert market["client"].get("/api/listing/nope").status_code == 404


def test_chain_route_reports_the_deployment(market):
    body = market["client"].get("/api/chain").json()
    assert body["mode"] == "chain"
    assert body["deployment"]["listing_contract"] == market["record"]["listing_contract"]


def test_health(market):
    assert market["client"].get("/api/health").json()["status"] == "ok"


def test_overview_totals_are_derived_from_the_listings(market):
    """The dashboard's figures come from the rows, not from a stored tally.

    A second source of truth is the thing this project argues against, so the
    check is that the aggregate equals the listings it summarises rather than
    that it equals some number written down when the listing was made.
    """
    _publish(market)
    body = market["client"].get("/api/overview").json()

    assert body["chain"] is True
    rows = body["listings"]
    assert body["totals"]["listings"] == len(rows)
    assert body["totals"]["volume_open"] == sum(
        int(r["listing"]["price"])
        for r in rows
        if r["listing"]["state"] in ("open", "escrowed")
    )
    assert body["totals"]["with_data_room"] == sum(
        1 for r in rows if r["has_metadata"]
    )


def test_overview_publishes_the_capability_model(market):
    """All nine directories appear, and the three generated ones are not for sale.

    Sourced from ``smp.py`` rather than restated, so this fails if the packager
    ever builds a directory the dashboard would not mention.
    """
    from succession.smp import DATA_CATEGORIES, GENERATED_CATEGORIES

    _publish(market)
    caps = market["client"].get("/api/overview").json()["capabilities"]

    assert [c["category"] for c in caps] == [
        *DATA_CATEGORIES,
        *GENERATED_CATEGORIES,
    ]
    live = {c["category"] for c in caps if c["transferable"]}
    assert live == set(DATA_CATEGORIES)
    assert all(c["status"] == "coming-soon" for c in caps if not c["transferable"])

    # The published listing described itself, so at least one directory has to
    # report records. A capability table that reads zero everywhere would pass a
    # weaker assertion while showing an empty screen.
    assert sum(c["records_sellable"] for c in caps) > 0
    assert all(c["note"] for c in caps)


def test_overview_publishes_the_reputation_weights_it_actually_uses(market):
    """The weights on screen are the constants the scorer computes with.

    A score whose weighting is documented separately can drift from the score,
    which is the same failure as a stored tally.
    """
    from succession import reputation as rep

    model = market["client"].get("/api/overview").json()["reputation_model"]
    published = {f["name"]: f["weight"] for f in model["factors"]}

    assert published == {
        "integrity": str(rep.W_INTEGRITY),
        "lineage": str(rep.W_LINEAGE),
        "continuity": str(rep.W_CONTINUITY),
        "earnings": str(rep.W_EARNINGS),
        "span": str(rep.W_SPAN),
    }
    assert sum(float(w) for w in published.values()) == pytest.approx(1.0)
    assert model["does_not_transfer"], "ACP standing must stay listed as non-transferable"


def test_demo_listings_are_excluded_from_every_figure(market):
    """The demo rows appear in the grid and in none of the numbers.

    This is the wall the whole demo-data decision rests on. If it ever comes
    down, the marketplace reports volume that nobody paid and a record count
    nobody accumulated, which is precisely the failure this project exists to
    argue against.
    """
    from service.demo import DEMO_PREFIX, demo_rows

    _publish(market)
    body = market["client"].get("/api/overview").json()

    real = body["listings"]
    demos = body["demo_listings"]

    assert len(demos) == len(demo_rows()), "demo rows must reach the client"
    assert demos, "the fixture is pointless if there are no demo rows"

    # The separation is structural: they are not in `listings` at all.
    assert all(not r["listing"]["listing_id"].startswith(DEMO_PREFIX) for r in real)
    # And each row still says what it is, so a client that concatenates the two
    # for display can still tell them apart afterwards.
    assert all(r["demo"] is True for r in demos)
    assert all(r["demo"] is False for r in real)

    # And none of them is counted anywhere.
    assert body["totals"]["listings"] == len(real)
    assert body["totals"]["volume_open"] == sum(
        int(r["listing"]["price"])
        for r in real
        if r["listing"]["state"] in ("open", "escrowed")
    )
    assert body["totals"]["volume_settled"] == sum(
        int(r["listing"]["price"]) for r in real if r["listing"]["state"] == "confirmed"
    )
    assert body["totals"]["with_data_room"] == sum(1 for r in real if r["has_metadata"])

    demo_sellable = sum(
        sum(v["sellable"] for v in r["preview"]["category_transferability"].values())
        for r in demos
    )
    assert demo_sellable > 0, "demo rows carry records, or they prove nothing here"
    assert (
        sum(c["records_sellable"] for c in body["capabilities"]) < demo_sellable
    ), "capability counts must not include demo records"


def test_a_demo_listing_cannot_be_bought(market):
    """No key produces the demo seller, so no chain write can be authorised.

    The UI disables the buttons, but a disabled button is a courtesy. The
    guarantee is that the seller address is unspendable.
    """
    from service.demo import demo_rows

    for row in demo_rows():
        assert row["listing"]["seller"] == "0x" + "0" * 40
        assert row["listing"]["buyer"] == ""
        # Nothing is escrowed against a demo row that is not also declared open.
        if row["listing"]["state"] == "open":
            assert row["listing"]["escrow_balance"] == 0


def test_a_demo_listing_resolves_by_url(market):
    """Listings are addressable now, so a demo listing needs an address too."""
    from service.demo import demo_rows

    target = demo_rows()[0]["listing"]["listing_id"]
    body = market["client"].get(f"/api/listing/{target}").json()
    assert body["listing"]["listing_id"] == target
    assert body["demo"] is True
    assert market["client"].get("/api/listing/demo-does-not-exist").status_code == 404


def test_listing_detail_matches_the_marketplace_row_shape(market):
    """A detail page must not render less than the row that linked to it."""
    _publish(market)
    listing_id = market["stored"].listing_id

    grid = market["client"].get("/api/marketplace").json()["listings"]
    row = next(r for r in grid if r["listing"]["listing_id"] == listing_id)
    detail = market["client"].get(f"/api/listing/{listing_id}").json()

    assert set(detail) == set(row)
    assert detail["agent_identity"] == row["agent_identity"]
    assert detail["has_metadata"] == row["has_metadata"] is True


def test_a_sale_completes_across_two_machines(market, tmp_path, monkeypatch):
    """The whole path, end to end, over a real socket and into a second store.

    This is the test the product needs and did not have. `succession fulfil`
    used to call `watch()` without a `deliver` callback, so it read the content
    key out of the vault, logged "key released" and transmitted nothing; the
    buyer's `succession claim` then 404ed on the key. Every existing test passed
    throughout, because each one exercised a single hop.

    Two things here are deliberate and are what give the test its teeth:

    * **A real HTTP server.** `TestClient` speaks ASGI in-process, which the CLI
      does not; the CLI uses `urllib`. Serving the same app object through
      uvicorn on a loopback port means the key genuinely crosses a socket, the
      seller signature genuinely travels in a header, and the marketplace URL is
      genuinely a URL.
    * **A separate store file.** The buyer imports into a database that did not
      exist when the test began, which is the closest a single process gets to
      the second machine this is meant to model.

    Only the chain wiring is substituted, because `_chain_backend` wants an RPC
    endpoint and a deployment file on disk. Everything the fix touched — the
    callback, the signature, the POST, the collection, the decrypt, the import
    and the re-derivation — runs for real.
    """
    import threading
    import time

    import uvicorn

    from succession import cli, publish as publish_module
    from succession.memory.sibyl import open_tenant

    listing_id = market["stored"].listing_id

    from service import app as app_module

    config = uvicorn.Config(
        app_module.app, host="127.0.0.1", port=0, log_level="error"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 20
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "the marketplace never came up"
    base = f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"

    try:
        # The buyer funds escrow. Until this lands the key must not move, and
        # the service checks that itself on both the accept and the serve.
        market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)

        # `SellerVault()` resolves a module-level default captured at import, so
        # the fixture's vault has to be named here for the CLI to find what it
        # published.
        monkeypatch.setattr(publish_module, "VAULT", tmp_path / "vault")
        monkeypatch.setattr(
            cli, "_chain_backend", lambda a, k: (market["backend"], market["record"])
        )
        monkeypatch.setenv("SUCCESSION_SIGNING_KEY", market["seller_key"])

        # Seller's machine. The fixture put the listing on chain; this is the
        # step that publishes it to the marketplace, and it is deliberately the
        # product's own code rather than the test helper `_publish`. Driving the
        # helper here is what hid the missing envelope upload: the test
        # performed a step no shipped command performed.
        assert cli.main(
            [
                "publish",
                "--listing", listing_id,
                "--marketplace", base,
                "--vault", str(tmp_path / "vault"),
            ]
        ) == 0, "the seller's own publish step must upload metadata and ciphertext"

        # The buyer can now reach the ciphertext. Before the fix this 404ed.
        assert (
            market["client"].get(f"/api/listing/{listing_id}/envelope").status_code
            == 200
        ), "the encrypted package must be published, or a paid buyer has nothing"

        assert cli.main(
            ["fulfil", "--listing", listing_id, "--once", "--marketplace", base]
        ) == 0

        # Buyer's machine: a store that did not exist a moment ago.
        buyer_db = tmp_path / "second-machine" / "memory.db"
        buyer_db.parent.mkdir(parents=True, exist_ok=True)
        assert cli.main(
            [
                "claim",
                "--listing", listing_id,
                "--db", str(buyer_db),
                "--tenant", "tenant-successor",
                "--marketplace", base,
            ]
        ) == 0, "claim returns non-zero when the re-derived root does not match"

        # `claim` exits 0 only on a verified import, so the assertion above is
        # already the hash check. This confirms the records are really resident
        # rather than the exit code being incidental.
        landed = open_tenant(buyer_db, "tenant-successor")
        records = (
            len(landed.entities())
            + len(landed.events())
            + len(landed.states())
            + len(landed.references())
        )
        assert records > 0, "the buyer's store is empty after a verified claim"
    finally:
        server.should_exit = True
        thread.join(timeout=15)


def test_fulfil_without_delivery_leaves_the_buyer_stranded(market, monkeypatch):
    """The regression guard, stated as the failure it prevents.

    `release_for` hands the key to `deliver` and returns released either way, so
    a caller that omits the callback gets a success report and moves nothing.
    That is precisely what the CLI did. This pins the behaviour so the next
    person to touch `cmd_fulfil` sees why the callback is not optional there.
    """
    from succession.fulfil import release_for

    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)

    outcome = release_for(listing_id, market["backend"], vault=market["vault"])
    assert outcome.released is True, "the chain does permit release"

    # And yet nothing reached the marketplace, so the buyer cannot collect.
    assert market["client"].get(f"/api/listing/{listing_id}/key").status_code == 404


def test_activity_reports_events_not_just_state(market):
    """The ledger says what happened, in order, with transactions attached."""
    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].buy(listing_id, buyer=market["buyer"], amount=PRICE)

    body = market["client"].get("/api/activity").json()
    assert body["chain"] is True

    kinds = [e["event"] for e in body["events"]]
    assert "Listed" in kinds and "Escrowed" in kinds

    # Newest first, so the escrow that just happened precedes the listing.
    assert kinds.index("Escrowed") < kinds.index("Listed")

    for event in body["events"]:
        assert event["tx"], "every row must trace to a transaction"
        assert event["block"] > 0
        # Bytes have to survive the JSON boundary as hex, not as a repr.
        for value in event["args"].values():
            assert not isinstance(value, (bytes, bytearray))

    escrowed = next(e for e in body["events"] if e["event"] == "Escrowed")
    assert escrowed["listing_id"] == listing_id
    assert escrowed["args"]["buyer"] == market["buyer"]


def test_activity_distinguishes_a_cancellation_from_a_refund(market):
    """The reason this endpoint exists.

    `cancel()` sets state to `Refunded` and emits `Cancelled`, so the listing
    struct cannot tell the two apart. Only the event can, and a marketplace that
    reported a seller's withdrawal as a failed delivery would be describing
    something that did not happen.
    """
    _publish(market)
    listing_id = market["stored"].listing_id
    market["backend"].cancel(listing_id)

    assert market["backend"].get(listing_id).state.value == "refunded"

    kinds = [
        e["event"]
        for e in market["client"].get("/api/activity").json()["events"]
        if e["listing_id"] == listing_id
    ]
    assert "Cancelled" in kinds
    assert "Refunded" not in kinds, "a cancellation must not read as a refund"
