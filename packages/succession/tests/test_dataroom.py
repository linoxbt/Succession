"""The preview must not leak. Not truncated, not snippeted, not by accident.

The spec's Day 7 instruction is to explicitly test that no code path in the
preview can leak private or non-transferable entity content. The strongest form
of that test is not "check these three fields" — it is to serialize the entire
preview and assert that no distinctive string from any withheld record appears
anywhere in it.
"""

from __future__ import annotations

import json

from succession.dataroom import build_preview
from succession.redaction import Sensitivity, read_disclosure


def _serialized(preview):
    return json.dumps(preview.to_dict(), default=str).lower()


def test_non_transferable_content_never_appears(seller, agent_id):
    preview = build_preview(seller, agent_identity=agent_id)
    blob = _serialized(preview)

    # The seed's one non-transferable counterparty, by every distinctive token.
    for secret in ("ironwood", "defense logistics", "forbids assignment", "nda"):
        assert secret not in blob, f"preview leaked {secret!r}"


def test_no_private_record_body_appears(seller, agent_id):
    """Sweep every non-public record in the tenant against the whole preview."""
    preview = build_preview(seller, agent_identity=agent_id)
    blob = _serialized(preview)

    leaked = []
    for entity in seller.entities():
        disclosure = read_disclosure(entity["body"])
        if disclosure.sensitivity == Sensitivity.PUBLIC and disclosure.transferable:
            continue
        for value in entity["body"].values():
            if isinstance(value, str) and len(value) > 12:
                if value.lower() in blob:
                    leaked.append((entity["name"], value))
    assert not leaked, f"preview leaked private content: {leaked}"


def test_journal_text_never_appears(seller, agent_id):
    preview = build_preview(seller, agent_identity=agent_id)
    blob = _serialized(preview)

    for event in seller.events():
        for line in event.get("acted") or []:
            assert line.lower() not in blob, f"preview leaked journal line: {line}"


def test_non_transferable_records_are_not_counted(seller, agent_id):
    """Counting withheld records would overstate the asset being sold."""
    preview = build_preview(seller, agent_identity=agent_id)

    assert preview.withheld_non_transferable == 1
    assert preview.counts["entities"] == len(seller.entities()) - 1
    assert "ironwood-defense-logistics" not in preview.public_counterparties


def test_only_public_counterparties_are_named(seller, agent_id):
    preview = build_preview(seller, agent_identity=agent_id)

    named = set(preview.public_counterparties)
    assert named == {"northwind-mills", "selkirk-timber"}
    for entity in seller.entities():
        if entity["category"] != "relationship":
            continue
        if read_disclosure(entity["body"]).sensitivity != Sensitivity.PUBLIC:
            assert entity["name"] not in named


def test_preview_reports_the_aggregates_a_buyer_needs(seller, agent_id):
    preview = build_preview(seller, agent_identity=agent_id)

    assert preview.tenure_days > 0
    assert preview.counts["journal_events"] > 0
    assert preview.memory_size_bytes > 0
    assert preview.valuation is not None
    assert preview.category_breakdown["relationship"] >= 5
