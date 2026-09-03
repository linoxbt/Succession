"""The valuation is a formula, so it is tested like one."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from succession.valuation import (
    DEFAULT_BASE_PRICE,
    PERFORMANCE_MAX,
    PERFORMANCE_MIN,
    RECENCY_MAX,
    RECENCY_MIN,
    trust_score,
    value_tenant,
)

NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def test_the_figure_is_the_product_of_its_factors(seller):
    valuation = value_tenant(seller, now=NOW)

    expected = valuation.base_price
    for factor in valuation.factors:
        expected *= factor.value
    assert valuation.amount == expected.quantize(Decimal("0.01"))


def test_it_is_deterministic(seller):
    assert value_tenant(seller, now=NOW).amount == value_tenant(seller, now=NOW).amount


def test_every_factor_explains_itself(seller):
    """A judge has to be able to re-derive this by hand, so each factor carries
    its own inputs and a sentence saying what it did with them."""
    for factor in value_tenant(seller, now=NOW).factors:
        assert factor.explanation
        assert factor.inputs
        assert Decimal(str(factor.value)) > 0


def test_the_five_factors_are_exactly_the_five_specified(seller):
    names = [f.name for f in value_tenant(seller, now=NOW).factors]
    assert names == [
        "tenure_factor",
        "interaction_density",
        "relationship_breadth",
        "task_performance",
        "recency_weight",
    ]


def test_demand_terms_are_declared_absent_rather_than_faked(seller):
    excluded = value_tenant(seller, now=NOW).to_dict()["excluded"]
    assert set(excluded) == {
        "buyer_demand",
        "origin_reputation",
        "buyer_satisfaction",
    }


def test_an_empty_tenant_still_produces_a_figure(buyer):
    """Every factor is clamped, so a tenant with no history lands at a floor
    rather than at zero or at something absurd."""
    valuation = value_tenant(buyer, now=NOW)
    assert valuation.amount > 0
    assert valuation.amount < DEFAULT_BASE_PRICE


def test_a_stale_tenant_is_worth_less_than_a_fresh_one(seller):
    fresh = value_tenant(seller, now=NOW)
    stale = value_tenant(seller, now=NOW + timedelta(days=365))
    assert stale.amount < fresh.amount

    fresh_recency = next(f for f in fresh.factors if f.name == "recency_weight")
    stale_recency = next(f for f in stale.factors if f.name == "recency_weight")
    assert fresh_recency.value > stale_recency.value
    assert stale_recency.value == RECENCY_MIN


def test_base_price_scales_the_result_linearly(seller):
    """Linear up to the cent the final figure is rounded to."""
    single = value_tenant(seller, base_price="100", now=NOW).amount
    double = value_tenant(seller, base_price="200", now=NOW).amount
    assert abs(double - single * 2) <= Decimal("0.01")


def test_the_figure_is_quantized_to_cents(seller):
    amount = value_tenant(seller, now=NOW).amount
    assert amount == amount.quantize(Decimal("0.01"))


# -- trust score ----------------------------------------------------------


def test_a_small_sample_scores_neutral():
    events = [{"acted": ["quoted and accepted"]} for _ in range(4)]
    score, counts = trust_score(events)
    assert score == Decimal("0.5")
    assert counts["resolved"] == 4


def test_a_clean_record_scores_high():
    events = [{"acted": ["quoted; accepted"]} for _ in range(10)]
    score, _ = trust_score(events)
    assert score == Decimal(1)


def test_losses_pull_the_score_down():
    events = [{"acted": ["accepted"]} for _ in range(6)] + [
        {"acted": ["declined"]} for _ in range(4)
    ]
    score, counts = trust_score(events)
    assert score == Decimal("0.6")
    assert counts == {"wins": 6, "losses": 4, "resolved": 10}


def test_unresolved_events_are_not_counted_as_losses():
    events = [{"acted": ["accepted"]} for _ in range(6)] + [
        {"acted": ["opened relationship with someone"]} for _ in range(20)
    ]
    score, counts = trust_score(events)
    assert counts["resolved"] == 6
    assert score == Decimal(1)


def test_performance_factor_stays_inside_its_band(seller):
    factor = next(
        f for f in value_tenant(seller, now=NOW).factors if f.name == "task_performance"
    )
    assert PERFORMANCE_MIN <= factor.value <= PERFORMANCE_MAX
