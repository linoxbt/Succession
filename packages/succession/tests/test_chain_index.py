from types import SimpleNamespace
import pytest

from succession.chain import listing_id_to_bytes32


def fake_chain(head, blocks, fail=False):
    def logs(*, from_block, to_block):
        if fail:
            raise ConnectionError('RPC unavailable')
        return [{'args': {'listingId': listing_id_to_bytes32(name)}, 'blockNumber': block}
                for name, block in blocks.items() if from_block <= block <= to_block]
    return SimpleNamespace(w3=SimpleNamespace(eth=SimpleNamespace(block_number=head)),
        contract=SimpleNamespace(events=SimpleNamespace(Listed=lambda: SimpleNamespace(get_logs=logs))))


def test_discovery_backfills_across_restarts_and_retains_old_listings(tmp_path):
    from service.chain_index import discover
    record = {'chain_id':84532, 'listing_contract':'0x'+'12'*20}
    db = tmp_path/'index.db'
    chain = fake_chain(30, {'old':1, 'new':29})
    first, progress = discover(chain, db, record, budget=2, span=10)
    assert first == ['new'] and not progress['complete']
    second, progress = discover(chain, db, record, budget=3, span=10)
    assert second == ['new', 'old'] and progress['complete']
    failed, progress = discover(fake_chain(35, {}, fail=True), db, record, budget=3, span=10)
    assert failed == second and progress['error']
    assert progress['indexed_to_block'] == 30
    resumed, progress = discover(fake_chain(35, {'old':1, 'new':29, 'latest':34}), db, record, budget=3, span=10)
    assert resumed == ['latest', 'new', 'old'] and progress['complete']


def test_reorg_replaces_recent_discovery_and_domains_are_separate(tmp_path):
    from service.chain_index import discover
    record = {'chain_id':84532, 'listing_contract':'0x'+'12'*20}
    db = tmp_path/'index.db'
    discover(fake_chain(10, {'removed':9}), db, record)
    ids, _ = discover(fake_chain(11, {'replacement':9}), db, record)
    assert ids == ['replacement']
    record['chain_id'] = 1
    ids, _ = discover(fake_chain(11, {}), db, record)
    assert ids == []
