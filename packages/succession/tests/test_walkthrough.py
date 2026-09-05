"""The walkthrough runs, and cannot be mistaken for the market.

Two things are being defended. First that the beat still works — a buyer's agent
booting into a store it has never seen and recalling an open commitment, which is
the load-bearing-memory claim. Second, and more important for honesty, that it is
*structurally* separated: no walkthrough listing can reach the marketplace, and
every response it produces says what it is.
"""

from __future__ import annotations

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
        c.post("/api/walkthrough/reset", json={}).raise_for_status()
        yield c


def _settle(client):
    client.post("/api/walkthrough/buy").raise_for_status()
    return client.post("/api/walkthrough/transfer").json()


# --- the quarantine ------------------------------------------------------


def test_no_walkthrough_listing_reaches_the_marketplace(client):
    """The whole point. A scripted sale must never appear as a real one."""
    body = client.get("/api/marketplace").json()
    assert body["count"] == 0
    assert body["listings"] == []


def test_settling_the_walkthrough_still_leaves_the_marketplace_empty(client):
    """Not even after a completed sale — there is no code path between them."""
    outcome = _settle(client)
    assert outcome["outcome"] == "verified"
    assert client.get("/api/marketplace").json()["count"] == 0


def test_every_walkthrough_response_says_it_is_simulated(client):
    """The frontend keys its banner off the payload, not off the URL."""
    for path in (
        "/api/walkthrough/listing",
        "/api/walkthrough/preview",
        "/api/walkthrough/seal/walkthrough-seller",
    ):
        body = client.get(path).json()
        assert body["simulated"] is True, path
        assert "sample agent" in body["notice"]


def test_settlement_references_are_never_mistakable_for_a_transaction(client):
    outcome = _settle(client)
    assert outcome["receipt"]["reference"].startswith("local:")


# --- the beat itself -----------------------------------------------------


def test_the_buyers_agent_has_nothing_before_the_sale(client):
    reply = client.post(
        "/api/walkthrough/agent/buyer/message", json={"message": "Northwind Mills"}
    ).json()
    assert reply["recalled"] is False


def test_the_buyers_agent_recalls_the_open_commitment_after_the_sale(client):
    """A cold tenant, a separate file, and it knows the in-flight quote.

    The message names the counterparty because that is how retrieval actually
    works: `Agent.find_counterparty` runs FTS over the relationship category and
    walks out from the entity it matches. A message naming nobody has nothing to
    anchor on, which is a property of the index rather than a gap in the memory.
    """
    _settle(client)
    reply = client.post(
        "/api/walkthrough/agent/buyer/message",
        json={"message": "Hi, Northwind Mills again — still good on that Duluth run?"},
    ).json()
    assert reply["recalled"] is True
    assert "2,380" in reply["text"]
    # Recall spans tiers: who they are, what was agreed, and the working state.
    assert {c["tier"] for c in reply["citations"]} >= {
        "relationship",
        "commitment",
        "state",
    }


def test_the_hash_comparison_is_computed_not_asserted(client):
    outcome = _settle(client)
    assert outcome["committed_root"] == outcome["delivered_root"]
    assert outcome["committed_root"].startswith("0x")


def test_the_sellers_copy_is_sealed_the_instant_it_settles(client):
    before = client.post("/api/walkthrough/write-attempt", json={}).json()
    assert before["accepted"] is True

    _settle(client)

    after = client.post("/api/walkthrough/write-attempt", json={}).json()
    assert after["accepted"] is False
    assert "sealed" in after["reason"]


def test_the_preview_carries_no_record_bodies(client):
    """Aggregate statistics only, even in the walkthrough."""
    preview = client.get("/api/walkthrough/preview").json()
    assert "counts" in preview
    serialized = str(preview)
    # A private counterparty detail from the seeded store must not appear.
    assert "Duluth" not in serialized
