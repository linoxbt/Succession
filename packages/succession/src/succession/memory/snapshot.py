"""One immutable source view shared by export, pricing and disclosure."""
import copy
from collections import Counter
from contextlib import nullcontext

from ..canonical import canonical_bytes
from ..smp import leaf_payload


class MemorySnapshot:
    def __init__(self, records, tenant_id, schema=None):
        self.records = copy.deepcopy(records)
        self.tenant_id = tenant_id
        self._schema = schema

    @classmethod
    def capture(cls, source):
        if isinstance(source, cls):
            return source
        from ..export import read_all
        with source.atomic_import() if hasattr(source, 'atomic_import') else nullcontext():
            return cls(read_all(source), source.tenant_id,
                       source.schema_version() if hasattr(source, 'schema_version') else None)

    def selected(self, package):
        from ..redaction import record_disclosure
        wanted = Counter(canonical_bytes(p) for rows in package.data.values() for p in rows)
        kept = []
        for record in self.records:
            if not record_disclosure(record).may_transfer:
                continue
            key = canonical_bytes(leaf_payload(record))
            if wanted[key]:
                kept.append(record)
                wanted[key] -= 1
        return MemorySnapshot(kept, self.tenant_id, self._schema)

    def schema_version(self): return self._schema
    def entities(self): return [r for r in self.records if r['kind']=='entity']
    def relations(self): return [r for r in self.records if r['kind']=='relation']
    def events(self): return [r for r in self.records if r['kind']=='event']
    def states(self): return [r for r in self.records if r['kind']=='state']
    def references(self): return [r for r in self.records if r['kind']=='reference']
    def archived(self): return [r for r in self.records if r['kind']=='archived']
