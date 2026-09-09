"""Adversarial cases reproduced during the September 2026 audit."""
import copy
import json
from pathlib import Path

import pytest

from succession.demokeys import SELLER, BUYER, EVALUATOR
from succession.export import export_tenant
from succession.importer import import_package, verify_package, ImportError_
from succession.redaction import mark, filter_transferable, Consent
from succession.dataroom import build_preview
from succession.settlement import LocalSettlement
from succession.seal import SealRegistry
from succession.transfer import execute_transfer, list_asset


def test_wallet_and_cli_share_the_same_authorization_message():
    from succession.auth import request_message
    vector = json.loads((Path(__file__).resolve().parents[3]/'fixtures/request-auth.json').read_text())
    fields = vector['inputs']
    assert request_message(**fields, method='GET', path=f"/api/listing/{fields['listing_id']}/key", body=b'') == vector['message']


@pytest.mark.parametrize('kind,field', [('event','extra'), ('relation','metadata'),
    ('reference','metadata'), ('reference','body'), ('entity','body'), ('state','body'), ('archived','body')])
@pytest.mark.parametrize('flags', [{'transferable':False}, {'consent':Consent.WITHHELD}])
def test_every_storage_tier_obeys_disclosure(kind, field, flags):
    record = {'kind':kind, field:mark({'secret':'must not leave'}, **flags)}
    kept, withheld, no_consent = filter_transferable([record])
    assert kept == []
    assert withheld + no_consent == 1


def test_private_journal_never_enters_export_or_preview(seller):
    seller.client.write_event(acted=['audit-private-content'], extra=mark({}, transferable=False))
    exported = export_tenant(seller,agent_identity=SELLER.agent_id,private_key=SELLER.private_key)
    assert 'audit-private-content' not in str(exported.package.to_dict())
    assert build_preview(seller,agent_identity=SELLER.agent_id).counts['journal_events'] == len(seller.events()) - 1


@pytest.mark.parametrize('tamper', ['permissions','manifest','categories','version'])
def test_generated_documents_are_bound_to_verified_package(seller, tamper):
    exported=export_tenant(seller,agent_identity=SELLER.agent_id,private_key=SELLER.private_key)
    package=copy.deepcopy(exported.package)
    if tamper=='permissions': package.permissions={'policy':'forged'}
    if tamper=='manifest': package.integrity['leaf_count'] += 1
    if tamper=='categories': package.header['categories']=[]
    if tamper=='version': package.header['smp_version']='unknown'
    with pytest.raises(ImportError_):
        verify_package(package,committed_root=exported.root_hex,expected_signer=SELLER.address)


def test_import_failure_rolls_back_all_tiers(seller,buyer,monkeypatch):
    exported=export_tenant(seller,agent_identity=SELLER.agent_id,private_key=SELLER.private_key)
    def fail(records):
        assert buyer.entities(), 'failure must occur after earlier writes'
        raise RuntimeError('disk failure after first tier')
    monkeypatch.setattr(buyer,'write_events',fail)
    with pytest.raises(RuntimeError,match='disk failure'):
        import_package(exported.package,buyer,committed_root=exported.root_hex,expected_signer=SELLER.address)
    assert buyer.is_empty()


def test_transfer_never_purges_an_occupied_destination(seller,buyer,tmp_path):
    backend=LocalSettlement(tmp_path/'escrow.db', arbiter=EVALUATOR.address)
    asset=list_asset(seller,backend,listing_id='occupied',agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,private_key=SELLER.private_key,price=100)
    backend.buy('occupied',buyer=BUYER.address,amount=100)
    buyer.client.set_entity('personal','keep',{'value':'irreplaceable'})
    from succession.evaluator import Evaluator
    from succession.memory.sibyl import open_tenant
    with pytest.raises(Exception, match='fresh tenant'):
        execute_transfer(listing_id='occupied',settlement=backend,seals=SealRegistry(tmp_path/'seals.db'),
            envelope=asset.envelope,content_key=asset.content_key,seller_tenant_id=seller.tenant_id,
            buyer_sink=buyer,evaluator_sink=open_tenant(tmp_path/'evaluator.db','evaluator'),
            evaluator=Evaluator(EVALUATOR.private_key),buyer_identity=BUYER.agent_id,
            buyer_address=BUYER.address,expected_signer=SELLER.address)
    assert backend.get('occupied').state.value == 'escrowed'
    assert buyer.client.get_entity('personal','keep')['body']=={'value':'irreplaceable'}


def test_partial_listing_preview_describes_only_selected_asset(seller,tmp_path):
    backend=LocalSettlement(tmp_path/'partial.db', arbiter=EVALUATOR.address)
    asset=list_asset(seller,backend,listing_id='scoped',agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,private_key=SELLER.private_key,price=100,categories=['preferences'])
    assert asset.preview.counts['total_records']==asset.export.record_count==4
    assert asset.preview.to_dict()['inventory']['relationships']['sellable']==0


def test_deliverable_is_durable_before_chain_and_uses_one_snapshot(seller,tmp_path,monkeypatch):
    from succession.publish import SellerVault, publish_listing
    from succession.envelope import open_envelope
    backend=LocalSettlement(tmp_path/'listing.db', arbiter=EVALUATOR.address)
    vault=SellerVault(tmp_path/'vault')
    original=backend.list_asset
    def commit(**terms):
        sid=terms['listing_id']
        assert vault.read(sid).stage=='prepared'
        package=open_envelope(vault.envelope(sid),vault.content_key(sid))
        verify_package(package,committed_root=terms['hash_commitment'],expected_signer=SELLER.address)
        seller.client.set_entity('relationship','arrived-during-broadcast',{'company':'too late for this sale'})
        return original(**terms)
    monkeypatch.setattr(backend,'list_asset',commit)
    stored,asset=publish_listing(seller,backend,agent_identity=SELLER.agent_id,
        private_key=SELLER.private_key,price=100,chain_id=84532,listing_contract='0x'+'12'*20,vault=vault)
    assert vault.read(stored.listing_id).stage=='listed'
    assert 'arrived-during-broadcast' not in str(asset.export.package.to_dict())
    assert stored.preview['counts']['total_records']==asset.export.record_count


def test_vault_failure_never_broadcasts(seller,tmp_path,monkeypatch):
    from succession.publish import SellerVault, publish_listing
    backend=LocalSettlement(tmp_path/'listing.db', arbiter=EVALUATOR.address)
    vault=SellerVault(tmp_path/'vault')
    def fail(*args,**kwargs): raise OSError('disk full')
    def unexpected(**kwargs): pytest.fail('broadcast before durable preparation')
    monkeypatch.setattr(vault,'write',fail)
    monkeypatch.setattr(backend,'list_asset',unexpected)
    with pytest.raises(OSError,match='disk full'):
        publish_listing(seller,backend,agent_identity=SELLER.agent_id,private_key=SELLER.private_key,
            price=100,chain_id=84532,listing_contract='0x'+'12'*20,vault=vault)


def test_prepared_listing_resumes_without_reexport_or_key_change(seller, tmp_path, monkeypatch):
    from succession.publish import SellerVault, publish_listing, resume_listing
    backend = LocalSettlement(tmp_path/'resume.db', arbiter=EVALUATOR.address)
    vault = SellerVault(tmp_path/'vault')
    original = backend.list_asset
    def fail(**kwargs):
        raise ConnectionError('broadcast unavailable')
    monkeypatch.setattr(backend, 'list_asset', fail)
    with pytest.raises(ConnectionError):
        publish_listing(seller, backend, agent_identity=SELLER.agent_id,
            private_key=SELLER.private_key, price=100, chain_id=84532,
            listing_contract='0x'+'12'*20, vault=vault)
    prepared = vault.all()[0]
    key = vault.content_key(prepared.listing_id)
    seller.client.set_entity('preference', 'changed-since-preparation', {'value':1})
    monkeypatch.setattr(backend, 'list_asset', original)
    resumed = resume_listing(prepared.listing_id, backend, private_key=SELLER.private_key, vault=vault)
    assert resumed.stage == 'listed'
    assert backend.get(resumed.listing_id).hash_commitment == prepared.committed_root
    assert vault.content_key(resumed.listing_id) == key
    assert resume_listing(resumed.listing_id, backend, private_key=SELLER.private_key, vault=vault) == resumed
