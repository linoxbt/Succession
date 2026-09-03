"""Virtuals ACP integration.

The live API is not reachable from CI, so these drive the same code paths
through a fake whose shape is taken from the real SDK — ``ACPJobPhase`` values,
``ACPJob`` field names, and the ``get_completed_jobs`` / ``get_cancelled_jobs``
pagination contract from ``virtuals-acp`` 0.3.23. What is *not* faked is
anything Succession itself computes: the history maths, the memory sync, the
valuation switch, and the registration gate all run for real.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from succession.acp import (
    ACP_CATEGORY,
    PHASE_COMPLETED,
    PHASE_EXPIRED,
    PHASE_REJECTED,
    ACPJobRecord,
    AgentNotRegistered,
    RecordedACP,
    fetch_history,
    job_history_from_memory,
    require_registered,
    sync_job_history,
)

AGENT = "0x1111111111111111111111111111111111111111"
CLIENT_A = "0xaaaa000000000000000000000000000000000001"
CLIENT_B = "0xaaaa000000000000000000000000000000000002"


def _job(job_id: int, phase: int = PHASE_COMPLETED, price: str = "25", client=CLIENT_A):
    return {
        "onchain_job_id": job_id,
        "phase": phase,
        "price": price,
        "token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "client_address": client,
        "provider_address": AGENT,
        "evaluator_address": "",
        "contract_address": "0x8Db6B1c839Fc8f6bd35777E194677B67b4D51928",
        "settled_at": "",
    }


def _snapshot(jobs, registered=True):
    return {
        "agent": (
            {
                "id": 417,
                "name": "Meridian Logistics Co.",
                "description": "Freight brokerage agent",
                "wallet_address": AGENT,
            }
            if registered
            else None
        ),
        "jobs": jobs,
    }


@pytest.fixture
def history():
    jobs = [_job(i) for i in range(1, 9)] + [
        _job(9, PHASE_REJECTED),
        _job(10, PHASE_EXPIRED, client=CLIENT_B),
        _job(11, price="40", client=CLIENT_B),
    ]
    return fetch_history(RecordedACP(_snapshot(jobs)))


# -- history maths --------------------------------------------------------


def test_completed_and_failed_are_separated(history):
    assert len(history.completed) == 9
    assert len(history.failed) == 2


def test_gross_volume_counts_only_completed_jobs(history):
    # 8 jobs at 25 plus one at 40. The rejected and expired ones earned nothing.
    assert history.gross_volume == Decimal("240")


def test_counterparties_are_the_other_side_of_each_job(history):
    assert history.counterparties == {CLIENT_A, CLIENT_B}


def test_counterparty_resolves_from_either_side():
    """The agent may be provider on one job and client on another."""
    as_provider = ACPJobRecord.from_dict(_job(1))
    assert as_provider.counterparty(AGENT) == CLIENT_A

    flipped = _job(2)
    flipped["client_address"], flipped["provider_address"] = AGENT, CLIENT_B
    assert ACPJobRecord.from_dict(flipped).counterparty(AGENT) == CLIENT_B


def test_success_rate_needs_a_real_sample():
    """Two-for-two is a small sample, not a 100% success rate."""
    small = fetch_history(RecordedACP(_snapshot([_job(1), _job(2)])))
    assert small.success_rate() is None

    enough = fetch_history(
        RecordedACP(_snapshot([_job(i) for i in range(1, 9)] + [_job(9, PHASE_REJECTED)]))
    )
    assert enough.success_rate() == Decimal(8) / Decimal(9)


def test_the_history_reports_verifiable_job_ids(history):
    blob = history.to_dict()
    assert blob["verifiable_job_ids"] == [1, 2, 3, 4, 5, 6, 7, 8, 11]
    assert blob["completed_jobs"] == 9
    assert blob["gross_volume"] == "240"


def test_price_is_carried_as_a_string_not_a_float():
    """Canonical serialization rejects floats, and a price that renders
    differently on two machines would break the integrity hash."""
    record = ACPJobRecord.from_dict(_job(1, price="25.5"))
    assert isinstance(record.price, str)

    from succession.canonical import canonical_bytes

    canonical_bytes(record.to_dict())  # must not raise


# -- the registration gate ------------------------------------------------


def test_an_unregistered_agent_cannot_be_listed():
    unregistered = fetch_history(RecordedACP(_snapshot([], registered=False)))
    with pytest.raises(AgentNotRegistered, match="service registry"):
        require_registered(unregistered)


def test_a_registered_agent_passes_the_gate(history):
    require_registered(history)
    assert history.registered is True
    assert history.agent_id == 417


# -- memory sync ----------------------------------------------------------


def test_sync_writes_job_history_into_memory(seller, history):
    written = sync_job_history(seller, history)
    assert written == len(history.jobs)

    stored = [e for e in seller.entities() if e["category"] == ACP_CATEGORY]
    assert len(stored) == len(history.jobs)
    assert seller.client.get_entity("identity", "acp-registration")["body"]["agent_id"] == 417


def test_sync_is_idempotent(seller, history):
    sync_job_history(seller, history)
    sync_job_history(seller, history)
    stored = [e for e in seller.entities() if e["category"] == ACP_CATEGORY]
    assert len(stored) == len(history.jobs), "re-syncing must update, not duplicate"


def test_history_round_trips_through_memory(seller, history):
    sync_job_history(seller, history)
    recovered = job_history_from_memory(seller)

    assert recovered.source == "memory"
    assert recovered.registered is True
    assert recovered.agent_address == AGENT
    assert len(recovered.completed) == len(history.completed)
    assert recovered.gross_volume == history.gross_volume
    assert recovered.counterparties == history.counterparties


def test_job_history_transfers_with_the_sale(seller, buyer, history, agent_id):
    """The point of the integration: the buyer inherits a verifiable earnings
    record, not just a claim about one."""
    from succession import export_tenant, import_package
    from succession.demokeys import SELLER

    sync_job_history(seller, history)
    exported = export_tenant(
        seller, agent_identity=agent_id, private_key=SELLER.private_key
    )
    result = import_package(
        exported.package,
        buyer,
        committed_root=exported.root_hex,
        expected_signer=SELLER.address,
    )
    assert result.verified

    inherited = job_history_from_memory(buyer)
    assert len(inherited.completed) == len(history.completed)
    assert inherited.gross_volume == history.gross_volume
    assert sorted(j.onchain_job_id for j in inherited.jobs) == sorted(
        j.onchain_job_id for j in history.jobs
    )


def test_acp_jobs_route_into_the_history_category(seller, history, agent_id):
    from succession.export import build_package

    sync_job_history(seller, history)
    package, _ = build_package(seller)

    origins = {
        r["origin"].get("category")
        for r in package.data["history"]
        if r["kind"] == "entity"
    }
    assert ACP_CATEGORY in origins


# -- the valuation switch -------------------------------------------------


def test_valuation_prefers_real_acp_outcomes(seller, history):
    from succession.valuation import value_tenant

    without = value_tenant(seller)
    with_acp = value_tenant(seller, acp_history=history)

    def performance(v):
        return next(f for f in v.factors if f.name == "task_performance")

    assert performance(without).inputs["basis"] == "journal"
    assert performance(with_acp).inputs["basis"] == "virtuals-acp"
    assert performance(with_acp).inputs["resolved"] == 11
    assert "on-chain job id" in performance(with_acp).explanation


def test_a_thin_acp_record_falls_back_to_the_journal(seller):
    """Too few settled jobs to be meaningful must not override the heuristic."""
    from succession.valuation import value_tenant

    thin = fetch_history(RecordedACP(_snapshot([_job(1), _job(2)])))
    factor = next(
        f
        for f in value_tenant(seller, acp_history=thin).factors
        if f.name == "task_performance"
    )
    assert factor.inputs["basis"] == "journal"


# -- the data room --------------------------------------------------------


def test_the_preview_labels_which_figures_are_verifiable(seller, history, agent_id):
    from succession.dataroom import build_preview

    sync_job_history(seller, history)
    blob = build_preview(seller, agent_identity=agent_id).to_dict()

    assert blob["acp"]["completed_jobs"] == 9
    assert blob["acp"]["registered"] is True
    assert "acp" in blob["provenance_of_figures"]["independently_verifiable"]
    assert "counts" in blob["provenance_of_figures"]["self_reported"]


def test_the_preview_works_for_an_agent_with_no_acp_history(seller, agent_id):
    from succession.dataroom import build_preview

    blob = build_preview(seller, agent_identity=agent_id).to_dict()
    assert blob["acp"] is None
    assert blob["provenance_of_figures"]["independently_verifiable"] == []


def test_the_preview_does_not_leak_acp_counterparty_addresses(seller, history, agent_id):
    """Job ids are the verifiable part. Counterparty wallets are not aggregates."""
    import json

    from succession.dataroom import build_preview

    sync_job_history(seller, history)
    blob = json.dumps(build_preview(seller, agent_identity=agent_id).to_dict()).lower()
    assert CLIENT_A.lower() not in blob
    assert CLIENT_B.lower() not in blob
