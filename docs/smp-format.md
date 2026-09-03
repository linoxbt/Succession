# Succession Memory Package — format specification v1.0

A self-contained, model-agnostic bundle describing one agent's memory at one
moment, with everything needed to verify that it is intact and that its owner
attested to it.

Sibyl Memory is the reference implementation of both ends. Nothing below is
specific to it.

---

## 1. Layout

```
succession-memory-package/
├── identity/           records.json
├── relationships/      records.json
├── preferences/        records.json
├── history/            records.json
├── commitments/        records.json
├── learned-behaviors/  records.json
├── provenance/         header.json
├── permissions/        disclosure.json
└── integrity-proof/    manifest.json
```

All nine directories are always present. The six data directories each hold:

```json
{ "included": true, "records": [ ... ] }
```

A category not part of a partial sale writes `"included": false` with an empty
list. That distinction matters: a buyer must be able to tell "sold, and empty"
from "not part of this transfer", and an empty array alone says both.

## 2. Categories

An SMP directory is a **selection unit**, not a storage location — it is what
partial succession filters on and what gets its own Merkle subroot. Every record
additionally carries an `origin` naming the tier and category it held in the
source engine, and that is what the importer re-keys against. So the grouping can
be opinionated without being lossy.

Default mapping from Sibyl's five tiers:

| SMP directory | Source |
|---|---|
| `identity/` | entity category `identity` |
| `relationships/` | entity category `relationship`; all WARM edges (`entity_relations`) |
| `preferences/` | entity category `preference` |
| `history/` | the COLD journal; ARCHIVE-tier entities; any unmapped entity category |
| `commitments/` | entity category `commitment`; HOT state documents |
| `learned-behaviors/` | entity category `learned-behavior`; REFERENCE documents |

Two of those edges are worth justifying. **HOT state lands in `commitments/`**
because live working state *is* the in-flight open work — it is what makes a
cutover continue a conversation rather than restart one. **REFERENCE documents
land in `learned-behaviors/`** because Sibyl's own learning pass writes accepted
skills to `reference/skill/<slug>`; they are literally this agent's encoded
behaviors.

`history/` is the catch-all for entity categories the map does not name. Because
`origin` is preserved, such a record still returns to its true category in the
buyer's store.

## 3. Canonical serialization

Everything hashed goes through one canonicalization:

- Object keys sorted by Unicode code point.
- No insignificant whitespace (`separators=(",", ":")`).
- UTF-8, NFC-normalized, so two visually identical strings hash the same.
- **Floats rejected.** JSON has no canonical float rendering that survives a
  round trip through every language's parser. Carry a fractional value as a
  string or a scaled integer.
- Duplicate keys after NFC normalization are an error, not a last-write-wins.

## 4. Ordering

Records within a directory sort by `(kind, primary key, content hash)`.

Grouping by kind keeps the journal contiguous and time-ordered inside `history/`
even though archived entities share the directory. The **content hash** breaks
ties rather than a row id, because row ids are regenerated on import and two
events written in the same millisecond must sort identically on both sides of a
transfer.

## 5. Leaf payloads

A leaf commits only to fields the import contract guarantees to reproduce
byte-for-byte. Engine row ids and destination-assigned `created_at`/`updated_at`
stamps are excluded — hashing them would make every honest import fail
verification. Journal `ts` *is* hashed, because `write_event` preserves it.

| Kind | Committed fields |
|---|---|
| `entity` | `origin{tier, category, name}`, `status`, `body` |
| `archived` | `origin{…}`, `archive_reason`, `body` |
| `event` | `origin{tier, ts}`, `evaluated`, `acted`, `forward`, `extra` |
| `state` | `origin{tier, key}`, `body` |
| `reference` | `origin{tier, key}`, `body`, `metadata` |
| `relation` | `origin{tier, from, to, relation_type}`, `metadata` |

The reserved `_succession` disclosure key is stripped before hashing. It records
the seller's disclosure decision, not the agent's memory, and carrying it across
would let a buyer's future export inherit the seller's redaction posture by
accident.

## 6. Integrity proof

Two-level Merkle tree, keccak256, RFC 6962 domain separation:

```
leaf(data)        = keccak256(0x00 ‖ data)
node(left, right) = keccak256(0x01 ‖ left ‖ right)
```

- A subtree per SMP category, over that category's leaves in canonical order.
- The root, over `leaf(canonical({category, subroot}))` for each category, in
  category-name order.

Distinct leaf and node prefixes stop the second-preimage attack where an
internal node is presented as a leaf. An odd node at any level is **promoted
unchanged**, never duplicated — duplication makes two different leaf multisets
produce the same root. Binding the category name to its subroot stops a cheap
directory being relabelled as an expensive one.

The root of an empty set is `keccak256("succession:smp:empty")`, distinct from
any real root.

`integrity-proof/manifest.json`:

```json
{
  "algorithm": "keccak256",
  "construction": "rfc6962-domain-separated",
  "root": "0x…",
  "leaf_count": 49,
  "categories": [ { "category": "relationships", "subroot": "0x…", "leaf_count": 13 } ]
}
```

### A note on partial verification

Every category's subroot is a function of its own content alone — **except
`relationships/`**, which carries the WARM edges. An edge is pruned before
hashing when the entity at its far end is not part of the sale, so that
category's content depends on which other categories travel with it. A partial
sale therefore commits its own root, computed over exactly what is being sold.

## 7. Provenance header

```json
{
  "smp_version": "1.0",
  "agent_identity": "erc8004:84532:0417",
  "created_at": "2026-09-05T10:14:02Z",
  "memory_version": 23,
  "categories": ["commitments", "history", "identity", "learned-behaviors", "preferences", "relationships"],
  "provenance_chain": [
    { "owner": "erc8004:84532:owner1", "acquired_at": "2026-06-01T00:00:00Z", "verified_hash": "0x…" }
  ],
  "integrity_root": "0x9f3a1c8e…c21edb04",
  "permissions_hash": "0x…",
  "signature": "0x…"
}
```

- **`memory_version`** is the count of COLD journal entries at export time. It
  needs no extra state and cannot drift from reality; a stored counter is one
  more thing that can be wrong, and a buyer has no way to audit it.
- **`permissions_hash`** binds the disclosure record into the signed structure.
  The permissions document is generated rather than exported, so it sits outside
  the tree over the memory itself; without this field the record of what was
  withheld would be the one part nobody attested to.
- **`provenance_chain`** grows by exactly one entry per change of hands. The
  post-sale journal write is where that entry is appended, so no separate lineage
  mechanism exists.

### Signing

EIP-191 personal-sign over:

```
SMP/1.0/provenance
<canonical JSON of the header with "signature" removed>
```

The spec's instruction is to sign `integrity_root`. Signing the whole header is
strictly stronger and still satisfies it, because the header contains the root.
Signing the bare root would leave `agent_identity`, `categories` and
`provenance_chain` unauthenticated — an intercepted package could keep a valid
signature while claiming to be a different, more valuable agent.

The domain tag prevents a signature here being replayed as a signature over some
other Succession structure that canonicalizes to the same bytes.

The on-chain commitment remains the bare `integrity_root`, so the contract-level
comparison is unchanged.

## 8. Permissions document

```json
{
  "policy_version": "1.0",
  "tiers": {
    "preview": "aggregate statistics only; no record bodies",
    "full": "every record in the package, post-purchase and hash-verified"
  },
  "redaction": {
    "withheld_non_transferable": 1,
    "withheld_by_category_filter": 0,
    "withheld_dangling_relations": 0,
    "categories_selected": ["…"]
  },
  "consent_basis": "…"
}
```

Counts only. Naming a withheld record would defeat the point of withholding it.

## 9. Delivery envelope

The package travels as AES-256-GCM ciphertext with the listing id and hash
commitment bound in as additional authenticated data. That binding means a
ciphertext prepared for one listing cannot be opened under another, so a buyer
cannot fund a cheap listing and be handed an expensive package.

The content key is escrowed alongside the payment and released only against
funded escrow. The Merkle commitment is over the **plaintext** package, so
encryption is orthogonal to integrity: the buyer decrypts, then verifies exactly
as they would have without it.

## 10. Import contract

A conforming importer MUST:

1. Verify the delivered root against the listing commitment, the header's own
   `integrity_root`, and the manifest — **before writing anything**.
2. Verify the header signature against the expected signer.
3. Refuse a non-empty destination tenant.
4. Write each record under the buyer's `tenant_id` at the position named by its
   `origin`, through the destination engine's public API.
5. Write edges last, resolving endpoints by logical key.
6. **Re-export the destination and re-derive the root**, and treat a mismatch as
   a failed transfer.

Step 6 is the one that matters. Steps 1-2 prove the courier was honest; step 6
proves the importer wrote what it received and the destination engine did not
silently coerce anything.
