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
