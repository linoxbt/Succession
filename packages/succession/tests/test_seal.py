"""The seller's copy is sealed the instant escrow releases.

This is the answer to "what stops the seller from just keeping a copy", and the
spec wants it demonstrated rather than asserted — the rehearsal includes an
on-camera write attempt that gets rejected. These tests are that beat, in CI.
"""

from __future__ import annotations

import pytest

from succession.seal import GuardedMemory, SealRegistry, TenantSealed


@pytest.fixture
def registry(tmp_path):
    return SealRegistry(tmp_path / "seals.db")


def test_writes_are_rejected_after_sealing(seller, registry):
    guarded = GuardedMemory(seller, registry)
    guarded.client.set_entity("preference", "pre-sale", {"ok": True})

    registry.seal(guarded.tenant_id, reason="sold")

    with pytest.raises(TenantSealed, match="live agent"):
        guarded.client.set_entity("preference", "post-sale", {"ok": False})


def test_every_write_path_is_gated(seller, registry):
    """One unguarded path is the whole hole. Check them all, by name."""
    guarded = GuardedMemory(seller, registry)
    registry.seal(guarded.tenant_id, reason="sold")

    with pytest.raises(TenantSealed):
        guarded.client.write_event(acted=["still trading"])
    with pytest.raises(TenantSealed):
        guarded.client.set_state("current-negotiation", {"x": 1})
    with pytest.raises(TenantSealed):
        guarded.client.set_reference("skill/anything", "text")
    with pytest.raises(TenantSealed):
        guarded.client.archive_entity("relationship", "northwind-mills")
    with pytest.raises(TenantSealed):
        guarded.client.delete_entity("relationship", "northwind-mills")

    for writer in (
        guarded.write_entities,
        guarded.write_events,
        guarded.write_states,
        guarded.write_references,
        guarded.write_archived,
        guarded.write_relations,
    ):
        with pytest.raises(TenantSealed):
            writer([])


def test_reads_still_work_after_sealing(seller, registry):
    """A sealed seller can still look at their history. They just cannot act."""
    guarded = GuardedMemory(seller, registry)
    registry.seal(guarded.tenant_id, reason="sold")

    assert guarded.client.get_entity("relationship", "northwind-mills")
    assert len(guarded.events()) > 0
    assert guarded.sealed is True


def test_sealing_is_idempotent_and_keeps_the_first_timestamp(seller, registry):
    first = registry.seal(seller.tenant_id, reason="sold")
    second = registry.seal(seller.tenant_id, reason="sold again")

    assert second.sealed_at == first.sealed_at
    assert second.reason == "sold"
    assert len(registry.list_sealed()) == 1


def test_an_unsealed_tenant_is_untouched(seller, registry):
    guarded = GuardedMemory(seller, registry)
    registry.seal("some-other-tenant", reason="sold")

    guarded.client.set_entity("preference", "still-fine", {"ok": True})
    assert guarded.sealed is False


def test_registry_has_no_unseal():
    """Sealing is permanent by construction, not by policy."""
    assert not hasattr(SealRegistry, "unseal")
