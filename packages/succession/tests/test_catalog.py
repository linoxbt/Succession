"""The marketplace population.

The thing worth testing here is not that the seeder writes rows — it is that
every figure the marketplace displays is *computed*. A marketplace of typed-in
numbers would look identical on screen and mean nothing.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from succession.catalog import CATALOG, NOW, archetype_by_slug, seed_archetype
from succession.demokeys import SELLER
from succession.export import export_tenant
from succession.dataroom import build_preview
from succession.memory.sibyl import open_tenant
from succession.valuation import value_tenant


@pytest.fixture
def market(tmp_path):
    """Every archetype, seeded into its own store."""
    out = []
    for archetype in CATALOG:
        memory = open_tenant(tmp_path / f"{archetype.slug}.db", archetype.tenant_id)
        seed_archetype(memory, archetype)
        out.append((archetype, memory))
    return out


def test_every_archetype_seeds_and_exports(market):
    for archetype, memory in market:
        exported = export_tenant(
            memory,
            agent_identity=archetype.agent_identity,
            private_key=SELLER.private_key,
        )
        assert exported.record_count > 0
        assert exported.root_hex.startswith("0x")


def test_every_listing_has_a_distinct_root(market):
    """Two listings sharing a root would mean two identical stores — or a bug
    that hashes something other than the memory."""
    roots = {
        export_tenant(
            m, agent_identity=a.agent_identity, private_key=SELLER.private_key
        ).root_hex
        for a, m in market
    }
    assert len(roots) == len(CATALOG)


def test_valuations_are_computed_and_differ(market):
    """The spread of prices has to come out of the data, not out of taste."""
    values = [value_tenant(m, now=NOW).amount for _, m in market]
    assert len(set(values)) == len(values)
    assert all(v > 0 for v in values)


def test_the_stale_agent_is_worth_least(market):
    """Cedar & Vale last acted 96 days ago; recency should price it last."""
    by_value = sorted(market, key=lambda pair: value_tenant(pair[1], now=NOW).amount)
    assert by_value[0][0].slug == "cedar-vale"


def test_asking_price_tracks_the_agents_own_valuation(market):
    """Price is derived, so the ask and the reference figure cannot contradict."""
    for archetype, memory in market:
        valuation = value_tenant(memory, now=NOW).amount
        ask = Decimal(archetype.asking_price(valuation)) / Decimal(1_000_000)
        assert abs(ask / valuation - Decimal(archetype.ask_ratio)) < Decimal("0.001")


def test_the_catalog_spans_both_sides_of_valuation(market):
    """A market where everyone asks over teaches a buyer nothing."""
    ratios = [Decimal(a.ask_ratio) for a in CATALOG]
    assert any(r > 1 for r in ratios)
    assert any(r < 1 for r in ratios)


def test_previews_never_leak_private_content(market):
    """The same sweep the featured listing gets, across every listing."""
    import json

    from succession.redaction import Sensitivity, read_disclosure

    for archetype, memory in market:
        blob = json.dumps(
            build_preview(memory, agent_identity=archetype.agent_identity, now=NOW).to_dict(),
            default=str,
        ).lower()
        for entity in memory.entities():
            disclosure = read_disclosure(entity["body"])
            if disclosure.sensitivity == Sensitivity.PUBLIC and disclosure.transferable:
                continue
            for value in entity["body"].values():
                if isinstance(value, str) and len(value) > 12:
                    assert value.lower() not in blob, f"{archetype.slug} leaked {value!r}"


def test_the_non_transferable_record_is_excluded(market):
    """Halcyon carries one. It must not reach the tree or the counts."""
    archetype = archetype_by_slug("halcyon-talent")
    memory = next(m for a, m in market if a.slug == "halcyon-talent")

    preview = build_preview(memory, agent_identity=archetype.agent_identity, now=NOW)
    assert preview.withheld_non_transferable == 1

    exported = export_tenant(
        memory, agent_identity=archetype.agent_identity, private_key=SELLER.private_key
    )
    names = {
        r["origin"].get("name")
        for records in exported.package.data.values()
        for r in records
        if r["kind"] == "entity"
    }
    assert "aperture-defense" not in names


def test_agents_recall_from_their_own_seeded_memory(market):
    """Each archetype's agent should answer from its own counterparties."""
    from succession.agent import Agent

    probes = {
        "halcyon-talent": ("backend engineer for Verity Systems", "Verity Systems"),
        "bright-harbor": ("Cobalt Studio here about the renewal", "Cobalt Studio"),
        "ironvane": ("Kessler Bearings, confirming the bearings volume", "Kessler Bearings"),
        "cedar-vale": ("Marlow Court renewals update", "Marlow Court"),
        "quantile-research": ("Aldervale Capital chasing the Q3 brief", "Aldervale Capital"),
    }
    for archetype, memory in market:
        question, expected = probes[archetype.slug]
        reply = Agent(memory).respond(question)
        assert reply.recalled, f"{archetype.slug} failed to recall"
        assert expected in reply.text
