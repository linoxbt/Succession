import pytest

from succession.acquisition import AcquisitionJournal
from succession.demokeys import SELLER, BUYER, EVALUATOR
from succession.envelope import open_envelope
from succession.settlement import LocalSettlement
from succession.transfer import list_asset


@pytest.fixture
def acquisition(seller, buyer, tmp_path):
    backend = LocalSettlement(tmp_path / 'settlement.db', arbiter=EVALUATOR.address)
    asset = list_asset(seller, backend, listing_id='journal', agent_identity=SELLER.agent_id,
                      seller_address=SELLER.address, private_key=SELLER.private_key, price=100)
    listing = backend.buy('journal', buyer=BUYER.address, amount=100)
    journal = AcquisitionJournal(buyer, {'chain_id':84532, 'listing_contract':'0x'+'12'*20}, listing, BUYER.address)
    package = open_envelope(asset.envelope, asset.content_key)
    return journal, package, backend


def test_retry_resumes_the_same_import_without_duplicate_records(acquisition):
    journal, package, _ = acquisition
    entry = journal.import_once(package)
    before = journal.sink.events()
    assert journal.import_once(None) == entry
    assert journal.sink.events() == before


def test_journal_failure_rolls_back_import(acquisition, monkeypatch):
    journal, package, _ = acquisition
    def fail(entry):
        raise OSError('journal disk error')
    monkeypatch.setattr(journal, '_write', fail)
    with pytest.raises(OSError):
        journal.import_once(package)
    assert journal.sink.is_empty()
    assert journal.read() is None


def test_changed_destination_cannot_confirm_a_stale_verified_root(acquisition):
    journal, package, _ = acquisition
    journal.import_once(package)
    journal.sink.client.set_entity('preference', 'modified-after-claim', {'value':1})
    with pytest.raises(ValueError, match='destination changed'):
        journal.import_once(None)


def test_completion_failure_is_resumable_and_idempotent(acquisition, monkeypatch):
    journal, package, backend = acquisition
    journal.import_once(package)
    receipt = backend.confirm_transfer('journal', delivered_hash=journal.listing.hash_commitment,
                                       buyer_identity=BUYER.address, caller=EVALUATOR.address)
    before = journal.sink.entities()
    original = journal.sink.write_events
    def fail(records):
        raise OSError('completion disk error')
    monkeypatch.setattr(journal.sink, 'write_events', fail)
    with pytest.raises(OSError):
        journal.complete(receipt)
    assert journal.sink.entities() == before
    assert journal.read()['stage'] == 'imported'
    monkeypatch.setattr(journal.sink, 'write_events', original)
    completed = journal.complete(receipt)
    assert completed['certificate']['settlement_reference'] == receipt.reference
    assert not completed['certificate']['seller_tenant_sealed_at']
    events = journal.sink.events()
    assert journal.complete(receipt) == completed
    assert journal.sink.events() == events


def test_resale_export_carries_completed_acquisition_history(acquisition):
    from succession.export import export_tenant
    from succession.importer import verify_package

    journal, package, backend = acquisition
    journal.import_once(package)
    receipt = backend.confirm_transfer('journal', delivered_hash=journal.listing.hash_commitment,
                                       buyer_identity=BUYER.address, caller=EVALUATOR.address)
    journal.complete(receipt)
    resold = export_tenant(journal.sink, agent_identity=package.header['agent_identity'],
                          private_key=BUYER.private_key)
    verify_package(resold.package, committed_root=resold.root_hex, expected_signer=BUYER.address)
    history = resold.package.header['provenance_chain']
    assert len(history) == 1
    assert history[0]['owner'] == BUYER.address
    assert history[0]['verified_hash'] == package.header['integrity_root']

    # A different identity and a withheld acquisition must not disclose this history.
    unrelated = export_tenant(journal.sink, agent_identity='erc8004:84532:99999',
                             private_key=BUYER.private_key)
    assert unrelated.package.header['provenance_chain'] == []
    record = journal.sink.client.get_entity('provenance', 'acquisition')
    from succession.redaction import RESERVED_KEY
    journal.sink.client.set_entity('provenance', 'acquisition',
                                  {**record['body'], RESERVED_KEY: {'transferable': False}})
    withheld = export_tenant(journal.sink, agent_identity=package.header['agent_identity'],
                            private_key=BUYER.private_key)
    assert withheld.package.header['provenance_chain'] == []
