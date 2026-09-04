"""Recall, through Sibyl's own index rather than a Python scan.

The cutover beat only means something if the agent retrieves from memory the
way a real one would. These pin the behaviour that makes the demo honest: a
returning customer who never says their company name still gets recognised,
because the lane and the notes are in the FTS index.
"""

from __future__ import annotations

import pytest

from succession.agent import Agent, _terms


@pytest.fixture
def agent(seller):
    return Agent(seller)


def test_recall_by_company_name(agent):
    reply = agent.respond("Hi, Northwind Mills again — still good on that Duluth run?")
    assert reply.recalled
    assert "Northwind Mills" in reply.text
    assert "2,380" in reply.text


def test_recall_by_lane_without_the_company_name(agent):
    """The realistic case: a customer says what they need, not who they are."""
    reply = agent.respond("We need a reefer from Yakima to Denver again")
    assert reply.recalled
    assert "Cascade Orchards" in reply.text


def test_recall_by_equipment_and_origin(agent):
    reply = agent.respond("Anything on the flatbed out of Coeur d'Alene?")
    assert reply.recalled
    assert "Selkirk Timber" in reply.text


def test_an_unknown_counterparty_is_not_invented(agent):
    """Retrieval that returns something for everything is not retrieval."""
    reply = agent.respond("Hello, this is Acme Widgets, we've never worked together")
    assert not reply.recalled
    assert reply.citations == []


def test_every_claim_carries_a_citation(agent):
    reply = agent.respond("Northwind Mills here about the Duluth run")
    tiers = {c.tier for c in reply.citations}
    assert {"relationship", "commitment", "state"} <= tiers


def test_recall_survives_a_transfer(seller, buyer, agent_id):
    """The point of the whole system: the buyer's cold agent recalls too."""
    from succession import export_tenant, import_package
    from succession.demokeys import SELLER

    exported = export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key
    )
    import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )
    reply = Agent(buyer).respond("We need a reefer from Yakima to Denver again")
    assert reply.recalled
    assert "Cascade Orchards" in reply.text


# -- term extraction ------------------------------------------------------


def test_terms_keep_domain_words_and_drop_filler():
    terms = [t.lower() for t in _terms("Hi, we need a reefer from Yakima to Denver")]
    assert "reefer" in terms
    assert "yakima" in terms
    assert "denver" in terms
    for filler in ("need", "from"):
        assert filler not in terms


def test_terms_are_deduplicated_and_bounded():
    terms = _terms("Duluth Duluth Duluth " + " ".join(f"word{i}" for i in range(20)))
    assert len(terms) <= 8
    assert len([t for t in terms if t.lower() == "duluth"]) == 1


def test_a_message_of_pure_filler_yields_no_terms():
    assert _terms("hi, how are you? we can do that") == []
