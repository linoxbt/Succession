# Sibyl Memory — setup and how Succession uses it

## Setup (Pro tier, free for the hackathon)

```bash
pip install 'sibyl-memory-cli[mcp]'
sibyl init      # opens a browser to activate; sign in with email or wallet
sibyl setup     # wires up Claude Code, Codex, Hermes — restart the app after
sibyl status    # confirms tier and where memory is stored
```

`sibyl init` writes `~/.sibyl-memory/credentials.json` and a SQLite store at
`~/.sibyl-memory/memory.db`.

Two environment variables matter for running seller and buyer side by side:

- `SIBYL_MEMORY_DB` — path to the store
- `SIBYL_TENANT_ID` — the active tenant

Succession passes both explicitly through `open_tenant(db_path, tenant_id)`, so
the demo never depends on ambient configuration.

**On the storage cap.** The free tier caps a store at 5 MB
(`FREE_TIER_CAP_BYTES` in the SDK — the build spec's 2 MB figure is out of
date). Pro lifts it for the event. Succession's seed data stays small anyway:
an export moves the entire store, and a compact, realistic seller is both truer
to the demo and cheaper to move.

---

## What breaks when memory is deleted

Delete the Sibyl Memory layer and Succession has nothing to sell. The product
is not an agent that uses memory — it is the ownership layer *for* memory, so
without it there is no asset, no hash to commit, no data room, and no cutover:
the buyer receives an empty tenant and the successor agent starts from nothing,
which is exactly the state the product exists to prevent.

## Memory walkthrough

**Persist.** All five tiers of the seller's tenant: WARM entities (identity,
counterparties, preferences, commitments, learned behaviours) and the edges
between them, HOT working state, the COLD journal, REFERENCE playbooks, and
ARCHIVE records. Verifiable Virtuals ACP job history is synced in as `acp-job`
entities, so the earnings record is part of the asset rather than a claim about
it.

**Recall (fresh session).** The buyer's agent boots on new infrastructure
against a tenant that was empty until the transfer landed. It retrieves through
Sibyl's FTS5 index (`search_entities`, anchored per category) plus keyed reads
of the open commitment and HOT working state. A returning customer who never
says their company name is still recognised, because the lane and the notes are
indexed — "we need a reefer from Yakima to Denver" resolves to Cascade
Orchards.

**Changes the agent's decision by.** It quotes as the incumbent rather than as
a stranger. It holds the open $2,380 Duluth → Kansas City quote at the price
already given, honours the hold through Monday from HOT state, refuses to go
under the margin floor from `preference/margin-floor`, and opens 4% above
target with counterparties whose learned behaviour is to counter. Without the
transferred memory every one of those is a fresh, worse quote.

## Primitives used

| Primitive | Where |
|---|---|
| **entities** | All six SMP categories are WARM entities, plus `entity_relations` edges re-linked by logical key on import |
| **recall** | Keyed `get_entity` / `get_state` reads for the open commitment and live working position — the cutover beat |
| **semantic search** | `search_entities` over the FTS5 index, per distinctive term, anchored to a category — how the agent finds a counterparty from a lane |
| **temporal** | The COLD journal is exported time-ordered and re-imported with original timestamps; `memory_version` is the journal count at export; the provenance chain records every change of hands |

Not claimed, because they are not used: summarization, reflection,
consolidation.

---

## Why the schema constraint matters here

Sibyl's `(tenant_id, category, name)` uniqueness is what makes "a clean,
exportable asset" true rather than aspirational. Succession leans on it twice:

- **Export** is deterministic because every record has exactly one logical key,
  so `(category, name)` ordering is total and the Merkle root is reproducible.
- **Import refuses a non-empty tenant.** Writing into one that already holds
  records would silently update on collision, and a silent update is data loss
  with a friendly message. Merging two independently-evolved memories is the
  `merge` primitive, and it is explicitly roadmap.
