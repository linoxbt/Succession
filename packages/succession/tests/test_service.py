"""The HTTP layer, exercised through the whole sale.

Routes are tested for the guarantees they are supposed to carry, not just for
200s — chiefly that the preview route cannot leak, and that the seal is visible
through the API the way it is in the library.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SUCCESSION_WORKDIR", str(tmp_path / "state"))
    for module in [m for m in list(sys.modules) if m.startswith("service")]:
        del sys.modules[module]
    from service.app import app

    with TestClient(app) as c:
        c.post("/api/demo/reset", json={}).raise_for_status()
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_the_listing_exposes_the_commitment(client):
    listing = client.get("/api/listing").json()
    assert listing["state"] == "open"
    assert listing["hash_commitment"].startswith("0x")
    assert listing["seller_signature"].startswith("0x")


def test_the_preview_route_does_not_leak(client):
    blob = json.dumps(client.get("/api/listing/preview").json()).lower()
    for secret in ("ironwood", "defense logistics", "forbids assignment"):
        assert secret not in blob


def test_the_buyers_agent_has_nothing_before_the_sale(client):
    reply = client.post(
        "/api/agent/buyer/message", json={"message": "Northwind Mills here"}
    ).json()
    assert reply["recalled"] is False


def test_the_sellers_agent_recalls_before_the_sale(client):
    reply = client.post(
        "/api/agent/seller/message", json={"message": "Northwind Mills here"}
    ).json()
    assert reply["recalled"] is True
    assert "2,380" in reply["text"]


def test_the_seller_can_write_before_the_sale(client):
    assert client.post("/api/seller/write-attempt", json={}).json()["accepted"] is True


def test_transfer_requires_escrow(client):
    assert client.post("/api/listing/transfer").status_code == 409


def test_the_full_sale_through_the_api(client):
    client.post("/api/listing/buy", json={}).raise_for_status()
    assert client.get("/api/listing").json()["state"] == "escrowed"

    outcome = client.post("/api/listing/transfer").json()
    assert outcome["outcome"] == "verified"
    assert outcome["committed_root"] == outcome["delivered_root"]
    assert outcome["certificate"]["transfer_status"] == "VERIFIED"
    assert "SUCCESSION CERTIFICATE" in outcome["certificate_text"]

    # The seller is sealed...
    assert client.get("/api/seal/tenant-seller").json()["sealed"] is True
    rejected = client.post("/api/seller/write-attempt", json={}).json()
    assert rejected["accepted"] is False
    assert "live agent" in rejected["reason"]

    # ...and the buyer's cold agent now recalls the in-flight quote.
    reply = client.post(
        "/api/agent/buyer/message",
        json={"message": "Hi, Northwind Mills again - still good on that Duluth run?"},
    ).json()
    assert reply["recalled"] is True
    assert "2,380" in reply["text"]
    assert {c["tier"] for c in reply["citations"]} >= {
        "relationship",
        "commitment",
        "state",
    }

    provenance = client.get("/api/agent/buyer/provenance").json()
    assert provenance["verified_hash"] == outcome["committed_root"]


def test_a_listing_cannot_be_bought_twice_over_http(client):
    client.post("/api/listing/buy", json={}).raise_for_status()
    assert client.post("/api/listing/buy", json={}).status_code == 409


def test_a_partial_listing_transfers_over_http(client):
    client.post(
        "/api/demo/reset", json={"categories": ["relationships", "preferences"]}
    ).raise_for_status()
    client.post("/api/listing/buy", json={}).raise_for_status()

    outcome = client.post("/api/listing/transfer").json()
    assert outcome["outcome"] == "verified"
    assert outcome["certificate"]["categories_transferred"] == [
        "preferences",
        "relationships",
    ]


# -- the settled outcome survives a reload --------------------------------


def test_outcome_is_404_before_settlement(client):
    """"Has not settled" and "failed" must not look the same to the console."""
    assert client.get("/api/listing/outcome").status_code == 404


def test_outcome_is_recoverable_after_settlement(client):
    """A settled sale must survive a page reload.

    The receipt is durable in settlement.db, but the certificate is assembled
    from the package header, which lives only in the listing process. Without a
    persisted outcome the confirmation screen and the ledger vanished on
    refresh for a transfer that genuinely happened — the UI asserting that
    nothing had occurred.
    """
    client.post("/api/listing/buy", json={}).raise_for_status()
    settled = client.post("/api/listing/transfer").json()

    recovered = client.get("/api/listing/outcome")

    assert recovered.status_code == 200
    body = recovered.json()
    assert body["outcome"] == "verified" == settled["outcome"]
    assert body["committed_root"] == settled["committed_root"]
    assert body["certificate"]["transfer_status"] == "VERIFIED"
    # The downloadable certificate is part of what has to survive; rebuilding
    # it from the header is exactly what a reload cannot do.
    assert body["certificate_text"]


def test_reset_clears_a_previous_outcome(client):
    """Otherwise a fresh demo opens showing the last sale's certificate."""
    client.post("/api/listing/buy", json={}).raise_for_status()
    client.post("/api/listing/transfer").raise_for_status()
    assert client.get("/api/listing/outcome").status_code == 200

    client.post("/api/demo/reset", json={}).raise_for_status()

    assert client.get("/api/listing/outcome").status_code == 404


# -- the settlement backend names itself ----------------------------------


def test_chain_route_reports_local_when_nothing_is_deployed(client, monkeypatch):
    """LocalSettlement must never be presentable as the chain."""
    monkeypatch.setenv("SUCCESSION_DEPLOYMENT", "/nonexistent/base-sepolia.json")

    body = client.get("/api/chain").json()

    assert body["mode"] == "local"
    assert body["deployment"] is None
    assert "No transaction reaches Base" in body["explanation"]


def test_chain_route_reports_the_deployment_when_one_exists(
    client, monkeypatch, tmp_path
):
    record = {
        "chain_id": 84532,
        "listing_contract": "0x" + "11" * 20,
        "identity_registry": "0x7177a6867296406881E20d6647232314736Dd09A",
        "identity_registry_is_mock": False,
        "payment_token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "arbiter": "0x" + "22" * 20,
    }
    path = tmp_path / "base-sepolia.json"
    path.write_text(json.dumps(record))
    monkeypatch.setenv("SUCCESSION_DEPLOYMENT", str(path))

    body = client.get("/api/chain").json()

    assert body["mode"] == "chain"
    assert body["chain_id"] == 84532
    assert body["deployment"]["identity_registry_is_mock"] is False


def test_chain_route_is_read_per_request_not_cached(client, monkeypatch, tmp_path):
    """Deploying happens while the service is already running.

    A value cached at import would keep reporting local mode until someone
    restarted it, which is the shape of bug that gets diagnosed as "the deploy
    silently failed".
    """
    path = tmp_path / "base-sepolia.json"
    monkeypatch.setenv("SUCCESSION_DEPLOYMENT", str(path))
    assert client.get("/api/chain").json()["mode"] == "local"

    path.write_text(json.dumps({"chain_id": 84532, "listing_contract": "0x0"}))

    assert client.get("/api/chain").json()["mode"] == "chain"
