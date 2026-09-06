"""The command handlers themselves, not the libraries underneath them.

An audit found that several subcommands had no coverage of their own wiring:
their library functions were tested thoroughly while the handler that calls
them, reads its arguments and chooses an exit code was never executed. That is
exactly the gap `succession fulfil` lived in — a well-tested `release_for`
beneath a handler that dropped the callback.

So every test here goes through `cli.main([...])` and asserts on the exit code,
because the exit code is the only thing a script or a CI job can read.
"""

from __future__ import annotations

import json

import pytest

from succession import cli
from succession.demokeys import SELLER

KEY_ENV = "SUCCESSION_SIGNING_KEY"
AGENT = "erc8004:84532:0417"


# --- audit ---------------------------------------------------------------


def test_audit_passes_against_a_memory_it_builds_itself(capsys):
    """The command a judge runs. No repo, no chain, no network, no fixtures."""
    assert cli.main(["audit"]) == 0
    out = capsys.readouterr().out
    assert "Succession, self-audit" in out
    assert "FAIL" not in out


def test_audit_reports_every_claim_as_machine_readable(capsys):
    body = json.loads(_json_audit(capsys))
    names = {c["name"] for c in body}

    # The set is the point: these are the claims the project makes in its
    # README and on its docs page, and each one has to be answered.
    assert {
        "categories-transfer",
        "withheld-absent-from-tree",
        "preview-has-no-bodies",
        "valuation-re-derives",
        "partial-takes-newest",
        "seal-rejects-writes",
        "published-manifests-match-chain",
    } <= names

    for check in body:
        assert check["status"] in {"passed", "failed", "skipped"}
        assert check["claim"], "a check with no stated claim proves nothing"
        assert check["detail"], "a check has to say what it found"


def test_audit_never_reports_an_unrunnable_check_as_passed(capsys):
    """A skipped check is not a passed one, and must not be counted as one."""
    body = json.loads(_json_audit(capsys))
    chain = next(c for c in body if c["name"] == "published-manifests-match-chain")
    # No --check-chain was passed, so it cannot have run.
    assert chain["status"] == "skipped"
    assert "marketplace" in chain["detail"]


def test_audit_exits_non_zero_when_a_claim_fails(monkeypatch, capsys):
    """The exit code is the contract. Without it the report is decoration."""
    from succession import audit as audit_module

    def broken(ctx):
        return audit_module.Check(
            "deliberately-broken", "A claim that is not true.", status="failed",
            detail="planted by the test",
        )

    monkeypatch.setattr(audit_module, "CHECKS", (*audit_module.CHECKS, broken))
    assert cli.main(["audit"]) == 1
    assert "deliberately-broken" in capsys.readouterr().out


def _json_audit(capsys) -> str:
    capsys.readouterr()
    cli.main(["audit", "--json"])
    return capsys.readouterr().out


# --- prove ---------------------------------------------------------------


def test_prove_certifies_every_category(monkeypatch, capsys, seller, tmp_path):
    monkeypatch.setenv(KEY_ENV, SELLER.private_key)
    assert cli.main([
        "prove", "--db", str(tmp_path / "seller.db"),
        "--tenant", "tenant-seller", "--agent", AGENT,
    ]) == 0
    out = capsys.readouterr().out
    assert "categories transferred intact" in out


def test_prove_certifies_a_partial_sale(monkeypatch, capsys, seller, tmp_path):
    """The shape the Sell page actually generates.

    `prove` took only whole categories, so a percentage sale — the default the
    moment any slider moves off 100 — could not be proved at all.
    """
    monkeypatch.setenv(KEY_ENV, SELLER.private_key)
    assert cli.main([
        "prove", "--db", str(tmp_path / "seller.db"),
        "--tenant", "tenant-seller", "--agent", AGENT,
        "--scope", "relationships=50,history=100",
    ]) == 0
    out = capsys.readouterr().out
    assert "relationships" in out and "history" in out


def test_prove_refuses_both_selection_mechanisms(monkeypatch, seller, tmp_path):
    monkeypatch.setenv(KEY_ENV, SELLER.private_key)
    with pytest.raises(SystemExit):
        cli.main([
            "prove", "--db", str(tmp_path / "seller.db"),
            "--tenant", "tenant-seller", "--agent", AGENT,
            "--categories", "history", "--scope", "history=50",
        ])


# --- argument hygiene ----------------------------------------------------


def test_a_misspelled_scope_category_is_refused_not_tracebacked(monkeypatch, tmp_path, seller):
    """`--categories` gets this from argparse; `--scope` is a free-form string."""
    monkeypatch.setenv(KEY_ENV, SELLER.private_key)
    with pytest.raises(SystemExit) as exc:
        cli.main([
            "prove", "--db", str(tmp_path / "seller.db"),
            "--tenant", "tenant-seller", "--agent", AGENT,
            "--scope", "relationshps=50",
        ])
    assert "unknown --scope category" in str(exc.value)


def test_inventory_reports_each_category(monkeypatch, capsys, seller, tmp_path):
    assert cli.main([
        "inventory", "--db", str(tmp_path / "seller.db"), "--tenant", "tenant-seller",
    ]) == 0
    out = capsys.readouterr().out
    for category in ("identity", "relationships", "history"):
        assert category in out


def test_listings_is_honest_about_an_empty_vault(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SUCCESSION_VAULT", str(tmp_path / "empty-vault"))
    from succession import publish as publish_module

    monkeypatch.setattr(publish_module, "VAULT", tmp_path / "empty-vault")
    assert cli.main(["listings"]) == 0
    assert "no listings" in capsys.readouterr().out.lower()
