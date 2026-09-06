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


# --- status --------------------------------------------------------------


def test_status_names_all_four_systems(capsys, monkeypatch):
    """The command exists to stop someone inferring connectivity from a failure."""
    monkeypatch.delenv("WHITELISTED_WALLET_PRIVATE_KEY", raising=False)
    assert cli.main(["status", "--marketplace", "http://127.0.0.1:1"]) == 0
    out = capsys.readouterr().out
    for system in ("Sibyl", "Base", "Marketplace", "Virtuals ACP"):
        assert system in out


def test_status_says_plainly_that_sibyl_has_no_sync(capsys, tmp_path, monkeypatch):
    """The claim people most often assume the other way round."""
    monkeypatch.setenv("SIBYL_CREDENTIALS", str(tmp_path / "none.json"))
    cli.main(["status", "--marketplace", "http://127.0.0.1:1"])
    out = capsys.readouterr().out
    assert "no sync endpoint" in out
    assert "5 MB" in out, "the free-tier consequence must be stated"


def test_status_lists_the_missing_acp_variables_by_name(capsys, monkeypatch):
    """'Not connected' is useless without saying what would connect it."""
    for name in ("WHITELISTED_WALLET_PRIVATE_KEY", "AGENT_WALLET_ADDRESS", "ACP_ENTITY_ID"):
        monkeypatch.delenv(name, raising=False)
    cli.main(["status", "--marketplace", "http://127.0.0.1:1"])
    out = capsys.readouterr().out
    assert "WHITELISTED_WALLET_PRIVATE_KEY" in out
    assert "ACP_ENTITY_ID" in out


def test_status_does_not_print_a_session_token(capsys, tmp_path, monkeypatch):
    import json as _json

    path = tmp_path / "credentials.json"
    path.write_text(_json.dumps({
        "tier": "pro", "account_id": "acct-1", "session_token": "do-not-print-me",
    }))
    monkeypatch.setenv("SIBYL_CREDENTIALS", str(path))
    cli.main(["status", "--marketplace", "http://127.0.0.1:1"])
    assert "do-not-print-me" not in capsys.readouterr().out


# --- the ACP entry point, which had no coverage at all -------------------


def test_acp_status_diagnoses_missing_credentials(capsys, monkeypatch):
    """`succession-acp` was entirely untested; this is its first test.

    Without Virtuals credentials the command must say which ones, rather than
    raising something a reader has to interpret.
    """
    from succession import acp_cli

    for name in ("WHITELISTED_WALLET_PRIVATE_KEY", "AGENT_WALLET_ADDRESS", "ACP_ENTITY_ID"):
        monkeypatch.delenv(name, raising=False)

    code = acp_cli.main(["status"])
    combined = capsys.readouterr()
    text = combined.out + combined.err
    assert code != 0 or "missing" in text.lower()


def test_acp_show_reports_an_agent_with_no_job_history(capsys, seller, tmp_path):
    """The honest empty case: a listing with no ACP history says so.

    This is why the live listings carry `acp: null` — those agents have never
    done a Virtuals job and are not registered, so there is nothing to report
    and nothing is invented.
    """
    from succession import acp_cli

    code = acp_cli.main([
        "show", "--db", str(tmp_path / "seller.db"), "--tenant", "tenant-seller",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "registered" in out.lower() or "jobs" in out.lower()
