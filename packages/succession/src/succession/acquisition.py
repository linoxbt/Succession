"""Durable buyer import and completion journal, committed with the memory writes."""
from dataclasses import asdict
import json

from .certificate import SuccessionCertificate
from .export import build_package
from .importer import ImportResult, import_package
from .merkle import to_hex
from .transfer import _write_post_sale_record


class AcquisitionJournal:
    def __init__(self, sink, deployment, listing, buyer):
        self.sink, self.listing, self.buyer = sink, listing, buyer
        self.storage = sink.client.storage
        self.key = (sink.tenant_id, int(deployment['chain_id']),
                    deployment['listing_contract'].lower(), listing.listing_id)
        with self.storage.connection() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS succession_acquisitions (
                tenant TEXT, chain_id INTEGER, contract TEXT, listing_id TEXT, payload TEXT NOT NULL,
                PRIMARY KEY (tenant, chain_id, contract, listing_id))''')

    def read(self):
        with self.storage.connection() as conn:
            row = conn.execute('''SELECT payload FROM succession_acquisitions
                WHERE tenant=? AND chain_id=? AND contract=? AND listing_id=?''', self.key).fetchone()
        if row is None:
            return None
        entry = json.loads(row['payload'])
        if (entry['buyer'].lower() != self.buyer.lower()
                or entry['result']['committed_root'].lower() != self.listing.hash_commitment.lower()
                or entry['result']['signer'].lower() != self.listing.seller.lower()):
            raise ValueError('acquisition journal does not match this buyer and on-chain asset')
        return entry

    def _write(self, entry):
        with self.storage.transaction() as conn:
            conn.execute('''INSERT INTO succession_acquisitions VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (tenant, chain_id, contract, listing_id) DO UPDATE SET payload=excluded.payload''',
                (*self.key, json.dumps(entry)))

    def verify_destination(self, entry):
        package, _ = build_package(self.sink, categories=entry['header']['categories'])
        root = to_hex(package.tree().root)
        if root.lower() != entry['result']['reimported_root'].lower():
            raise ValueError('destination changed after import; refusing to confirm a stale root')

    def import_once(self, package, *, from_block=0):
        with self.sink.atomic_import():
            entry = self.read()
            if entry is not None:
                if entry['stage'] != 'complete':
                    self.verify_destination(entry)
                return entry
            result = import_package(package, self.sink,
                committed_root=self.listing.hash_commitment, expected_signer=self.listing.seller)
            entry = {'stage': 'imported', 'buyer': self.buyer, 'header': package.header,
                     'result': asdict(result), 'from_block': from_block}
            self._write(entry)
            return entry

    def complete(self, receipt):
        if (receipt.listing_id != self.listing.listing_id or receipt.outcome != 'released'
                or receipt.identity_transferred_to.lower() != self.buyer.lower()):
            raise ValueError('settlement receipt does not confirm this acquisition')
        with self.sink.atomic_import():
            entry = self.read()
            if entry is None:
                raise ValueError('no verified local claim exists for this listing')
            if entry['stage'] == 'complete':
                return entry
            self.verify_destination(entry)
            result = ImportResult(**entry['result'])
            _write_post_sale_record(self.sink, header=entry['header'], listing=self.listing,
                receipt=receipt, verified_hash=result.reimported_root, buyer_identity=self.buyer)
            certificate = SuccessionCertificate.from_transfer(header=entry['header'],
                import_result=result, transfer_date=receipt.settled_at,
                successor_agent=self.buyer, settlement_reference=receipt.reference)
            entry.update(stage='complete', receipt=receipt.to_dict(), certificate=certificate.to_dict())
            self._write(entry)
            return entry
