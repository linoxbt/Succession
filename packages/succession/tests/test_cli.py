"""The CLI, driven the way the two-machine rehearsal drives it.

Export writes a package to disk; verify and import read it back in a separate
call, against a separate store. Nothing is passed in memory between the two
halves, which is the whole point — this is the path that works when the two
halves are on different hosts.
"""

from __future__ import annotations

import json

import pytest

from succession.cli import main
from succession.demokeys import SELLER


@pytest.fixture
def exported(seller, tmp_path, monkeypatch, agent_id):
    monkeypatch.setenv("SUCCESSION_SIGNING_KEY", SELLER.private_key)
    out = tmp_path / "pkg"
    assert (
        main(
            [
                "export",
                "--db", str(seller.client.storage.db_path),
                "--tenant", seller.tenant_id,
                "--agent", agent_id,
                "--out", str(out),
            ]
        )
        == 0
    )
    header = json.loads((out / "provenance" / "header.json").read_text())
    return out, header["integrity_root"]


def test_export_requires_the_key_from_the_environment(seller, tmp_path, monkeypatch, agent_id):
    """A private key on a command line lands in shell history and `ps` output."""
    monkeypatch.delenv("SUCCESSION_SIGNING_KEY", raising=False)
    with pytest.raises(SystemExit, match="SUCCESSION_SIGNING_KEY"):
        main(
            [
                "export",
                "--db", str(seller.client.storage.db_path),
                "--tenant", seller.tenant_id,
                "--agent", agent_id,
                "--out", str(tmp_path / "pkg"),
            ]
        )


def test_verify_then_import_across_separate_calls(exported, tmp_path, capsys):
    package, root = exported

    assert main(["verify", str(package), "--root", root, "--signer", SELLER.address]) == 0

    assert (
        main(
            [
                "import", str(package),
                "--db", str(tmp_path / "buyer.db"),
                "--tenant", "t-buyer",
                "--root", root,
                "--signer", SELLER.address,
            ]
        )
        == 0
    )
    assert "VERIFIED" in capsys.readouterr().out


def test_verify_exits_nonzero_on_a_tampered_package(exported, capsys):
    package, root = exported
    path = package / "preferences" / "records.json"
    blob = json.loads(path.read_text())
    blob["records"][0]["body"]["tampered"] = True
    path.write_text(json.dumps(blob))

    assert main(["verify", str(package), "--root", root, "--signer", SELLER.address]) == 1
    assert "FAILED" in capsys.readouterr().err


def test_verify_exits_nonzero_against_the_wrong_signer(exported):
    package, root = exported
    from succession.demokeys import BUYER

    assert main(["verify", str(package), "--root", root, "--signer", BUYER.address]) == 1


def test_import_refuses_a_tampered_package(exported, tmp_path):
    package, root = exported
    path = package / "history" / "records.json"
    blob = json.loads(path.read_text())
    blob["records"].pop()
    path.write_text(json.dumps(blob))

    assert (
        main(
            [
                "import", str(package),
                "--db", str(tmp_path / "buyer.db"),
                "--tenant", "t-buyer",
                "--root", root,
                "--signer", SELLER.address,
            ]
        )
        == 1
    )


def test_inspect_reports_the_recomputed_root(exported, capsys):
    package, root = exported
    assert main(["inspect", str(package)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["recomputed_root"] == root
    assert report["matches_header"] is True


def test_value_and_preview_emit_json(seller, capsys, agent_id):
    db, tenant = str(seller.client.storage.db_path), seller.tenant_id

    assert main(["value", "--db", db, "--tenant", tenant]) == 0
    assert "factors" in json.loads(capsys.readouterr().out)

    assert main(["preview", "--db", db, "--tenant", tenant, "--agent", agent_id]) == 0
    assert "counts" in json.loads(capsys.readouterr().out)


def test_a_partial_export_round_trips_through_the_cli(
    seller, tmp_path, monkeypatch, agent_id, capsys
):
    monkeypatch.setenv("SUCCESSION_SIGNING_KEY", SELLER.private_key)
    out = tmp_path / "partial"
    assert (
        main(
            [
                "export",
                "--db", str(seller.client.storage.db_path),
                "--tenant", seller.tenant_id,
                "--agent", agent_id,
                "--out", str(out),
                "--categories", "relationships", "preferences",
            ]
        )
        == 0
    )
    capsys.readouterr()
    root = json.loads((out / "provenance" / "header.json").read_text())["integrity_root"]

    assert (
        main(
            [
                "import", str(out),
                "--db", str(tmp_path / "partial-buyer.db"),
                "--tenant", "t-partial",
                "--root", root,
                "--signer", SELLER.address,
            ]
        )
        == 0
    )
