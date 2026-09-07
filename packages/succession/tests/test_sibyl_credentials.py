"""The bridge to Sibyl's own credentials, and what it must never do.

Succession shares a SQLite file with the Sibyl CLI and nothing else: the SDK's
whole network surface is a capacity check and a heartbeat carrying an integer.
So the only meaningful "connect to Sibyl" work is passing through the account
the CLI already wrote, which is what stops a paying customer being silently
treated as free tier under a strict 5 MB cap.

The tests that matter most here are the ones asserting it degrades quietly. An
export must not fail because a JSON file had a trailing comma.
"""

from __future__ import annotations

import json

from succession.memory.credentials import (
    CREDENTIALS_ENV,
    TIER_ENV,
    load_credentials,
)


def test_no_credentials_file_is_the_free_tier_and_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv(CREDENTIALS_ENV, str(tmp_path / "nothing.json"))
    monkeypatch.delenv(TIER_ENV, raising=False)

    creds = load_credentials()
    assert creds.tier == "free"
    assert creds.connected is False
    assert creds.kwargs() == {"tier": "free"}
    assert "5 MB" in creds.describe(), "the consequence has to be stated, not implied"


def test_a_paid_account_is_carried_through(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({
        "tier": "lifetime",
        "account_id": "acct-123",
        "session_token": "tok-abc",
        "claim": {"tier": "lifetime"},
        "signature": "0xsig",
    }))
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    monkeypatch.delenv(TIER_ENV, raising=False)

    creds = load_credentials()
    assert creds.connected is True
    assert creds.kwargs() == {
        "tier": "lifetime",
        "account_id": "acct-123",
        "session_token": "tok-abc",
        "credentials_claim": {"tier": "lifetime"},
        "credentials_signature": "0xsig",
    }


def test_a_malformed_file_degrades_rather_than_raising(tmp_path, monkeypatch):
    """A seller mid-export must not lose a package to a stray comma."""
    path = tmp_path / "credentials.json"
    path.write_text("{ not json at all ,,, }")
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    monkeypatch.delenv(TIER_ENV, raising=False)

    creds = load_credentials()
    assert creds.tier == "free"
    assert creds.connected is False
    assert "unreadable" in creds.source


def test_the_environment_overrides_the_file(tmp_path, monkeypatch):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"tier": "free", "account_id": "a", "session_token": "b"}))
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    monkeypatch.setenv(TIER_ENV, "pro")

    assert load_credentials().tier == "pro"


def test_a_token_is_never_put_in_the_description(tmp_path, monkeypatch):
    """`status` prints this. A session token must not land in a terminal log."""
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({
        "tier": "pro", "account_id": "acct-123", "session_token": "super-secret-token",
    }))
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    monkeypatch.delenv(TIER_ENV, raising=False)

    described = load_credentials().describe()
    assert "super-secret-token" not in described
    assert "acct-123" in described


def test_opening_a_store_applies_them(tmp_path, monkeypatch):
    """The wiring, not just the parsing: `open_tenant` has to pass them on."""
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"tier": "lifetime", "account_id": "a", "session_token": "b"}))
    monkeypatch.setenv(CREDENTIALS_ENV, str(path))
    monkeypatch.delenv(TIER_ENV, raising=False)

    seen: dict = {}
    import sibyl_memory_client

    original = sibyl_memory_client.MemoryClient.local

    def spy(cls_path, **kwargs):
        seen.update(kwargs)
        return original(cls_path, **kwargs)

    monkeypatch.setattr(sibyl_memory_client.MemoryClient, "local", spy)

    from succession.memory.sibyl import open_tenant

    open_tenant(tmp_path / "store.db", "t")
    assert seen.get("tier") == "lifetime"
    assert seen.get("account_id") == "a"
    assert seen.get("session_token") == "b"


# --- the rest of the SDK surface -----------------------------------------


def test_store_health_reports_what_the_engine_knows(tmp_path):
    """Succession used 17 of MemoryClient's 26 methods and ignored the nine
    that describe a store's state rather than its contents. For a marketplace
    those are the interesting ones: capacity, schema, and what is unresolved.
    """
    from succession.memory.sibyl import open_tenant

    memory = open_tenant(tmp_path / "s.db", "t")
    health = memory.store_health()

    assert set(health) == {
        "tier", "schema_version", "capacity", "pending_skill_proposals", "lint",
    }
    assert health["schema_version"] is not None, "the engine reports a schema version"

    capacity = health["capacity"]
    assert capacity["soft_cap_bytes"] > 0
    assert 0 <= capacity["pct_used"] <= 1
    assert capacity["at_or_above_cap"] is False


def test_paid_features_degrade_to_none_rather_than_raising(tmp_path):
    """Three of the four are paid-tier. A free account must still export."""
    from succession.memory.sibyl import open_tenant

    health = open_tenant(tmp_path / "s.db", "t").store_health()
    assert health["pending_skill_proposals"] is None
    assert health["lint"] is None


def test_the_package_header_carries_the_engine_schema_version(tmp_path, seller):
    """A buyer needs to know their store can accept the package before paying.

    Signed with the rest of the header, so it is not a claim the seller could
    edit after the fact.
    """
    from succession.demokeys import SELLER
    from succession.export import export_tenant

    result = export_tenant(
        seller, agent_identity="erc8004:84532:0417", private_key=SELLER.private_key
    )
    header = result.package.header
    assert "engine_schema_version" in header
    assert header["engine_schema_version"] == seller.schema_version()

    # And it is inside the signature, not appended beside it: tampering with
    # the field has to break verification.
    from succession.provenance import SignatureError, verify_header

    verify_header(header, expected_signer=SELLER.address)

    forged = dict(header)
    forged["engine_schema_version"] = 999
    try:
        verify_header(forged, expected_signer=SELLER.address)
    except SignatureError:
        pass
    else:
        raise AssertionError("the schema version is outside the signature")
