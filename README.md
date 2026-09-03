# Succession

**The property layer for agent memory.**

Code gives an agent capability. A model gives it reasoning. Memory gives it
continuity — and Succession gives that continuity an economic life beyond the
original agent. The code can be replaced. The model can be replaced. The wallet
can be replaced. The accumulated relationships, preferences, history and context
are what actually can't be.

The business analogy: the model and code are the employee; the accumulated
memory is the customer book. Succession does not sell the employee. It makes the
customer book itself a transferable asset.

---

## What actually happens

A seller exports their agent's full Sibyl Memory into a **Succession Memory
Package**, commits a Merkle root of it on Base, signs that commitment with the
key holding the agent's ERC-8004 identity, and lists it. A buyer funds escrow.
The package is delivered encrypted, imported into a brand-new tenant, and
**re-hashed there**. Only if the root the buyer derives from their own store
matches the one committed before a buyer existed does escrow release — and when
it does, payment, the ERC-8004 identity transfer, and the seal on the seller's
copy all happen in a single transaction.

The buyer's agent then boots cold, on new infrastructure, and continues a live
customer relationship exactly where the seller's agent left off.

```
  seller tenant                                          buyer tenant
       │                                                      ▲
       │  1. filter → serialize → hash → sign                 │
       ▼                                                      │
  SMP package ──2. commit root──▶ ListingContract (Base)       │
       │                              │                       │
       │                       3. buyer funds escrow           │
       │                              │                       │
       └──4. AES-256-GCM envelope, key released on escrow──────┘
                                      │                  5. import + RE-HASH
                                      ▼                       │
                        6. confirmTransfer(deliveredRoot) ◀────┘
                           ├─ release payment to seller
                           ├─ transfer ERC-8004 identity
                           └─ set sealed flag        ── all three, or none
```

### Why this is hard to fake

Anyone can build a UI that says "transfer complete". What is here instead:

- **The commitment precedes the buyer.** The root is posted at listing time, so
  it cannot be computed after the fact to match whatever was delivered.
- **Verification re-hashes the destination, not the wire.** Checking the bytes
  received only proves the courier was honest. Re-exporting the buyer's own
  store and re-deriving the root proves the importer wrote what it received and
  the destination engine did not silently coerce anything.
- **The signature covers the whole provenance header**, not just the root — so
  an intercepted package cannot keep a valid signature while claiming to be a
  different, more valuable agent.
- **Two genuinely separate stores.** The test suite gives seller and buyer their
  own SQLite files, and the demo takes `--seller-dir`/`--buyer-dir` so the halves
  can run on separate machines. Two browser tabs on one database would pass a
  demo and fail every test here.
- **The seller's copy is sealed** the instant escrow releases, at both the
  contract level and the memory-service level.

---

## Repository layout

```
packages/succession/   the pipeline: SMP format, Merkle tree, provenance,
                       redaction, valuation, sealing, settlement, transfer
contracts/             ListingContract.sol and the ERC-8004 / ERC-20 interfaces
service/               a thin FastAPI layer over the pipeline
web/                   the marketplace UI (React + Vite + Tailwind)
docs/                  the SMP format spec and the threat model
```

## Running it

```bash
# the pipeline and its tests
python -m venv .venv && .venv/bin/pip install -e "packages/succession[dev,service]"
.venv/bin/python -m pytest packages/succession/tests

# the contracts (Foundry is the toolchain; solc via npm is the fallback)
cd contracts && npm install && npm run build && forge test

# the whole workflow, on the console
.venv/bin/python -m succession.demo

# the UI
PYTHONPATH=. .venv/bin/uvicorn service.app:app --port 8000
cd web && npm install && npm run dev
```

---

## The Succession Memory Package

Nine directories, six carrying data and three generated at build time:

```
succession-memory-package/
├── identity/           agent identity, ERC-8004 reference, package version
├── relationships/      per-counterparty entities, and the edges between them
├── preferences/        learned preferences and settings
├── history/            the time-ordered journal, plus archived records
├── commitments/        open promises, quotes given, terms agreed, live state
├── learned-behaviors/  patterns, heuristics, and encoded playbooks
├── provenance/         origin, version, prior-owner chain, signature
├── permissions/        redaction flags, consent basis, access tiers
└── integrity-proof/    Merkle root + per-category subroots
```

Two ideas make this a format rather than a database dump:

**An SMP directory is a selection unit, not a storage location.** It is what
partial succession filters on and what gets its own Merkle subroot — a
disclosure boundary a seller reasons about ("sell the relationships, keep the
commitments"), which is why the standard fixes six of them rather than mirroring
whatever categories a given engine happens to use.

**Every record carries its `origin`** — the exact tier and category it held in
the source engine. That is what the importer re-keys against, so the directory
grouping can be opinionated without ever being lossy.

Sibyl Memory is this build's reference implementation, behind a
`MemorySource`/`MemorySink` adapter. A second, non-Sibyl engine importing a real
SMP package is the strongest possible proof that this is a protocol and not a
feature — and it is explicitly **not** attempted here.

Full format spec: [`docs/smp-format.md`](docs/smp-format.md).

### The integrity scheme

A two-level Merkle tree: a subroot per SMP category, then a root over the
`(category, subroot)` pairs. Leaves and internal nodes are domain-separated
RFC 6962 style, and an odd node is promoted rather than duplicated — those are
the two known forgery vectors. Binding the category name to its subroot means a
seller cannot relabel a cheap directory as an expensive one.

The two-level shape is what makes partial succession verifiable without a
redesign. A flat hash would have needed one.

A leaf commits only to what the import contract guarantees to reproduce
byte-for-byte. Engine row ids and destination-assigned timestamps are
deliberately excluded: hashing them would mean an honest, correct import always
fails verification, turning the integrity check into noise.

---

## Valuation

Deterministic, inspectable, and re-derivable by hand:

```
valuation = base_price
          × tenure_factor        age of the tenant
          × interaction_density  journal events per day over that tenure
          × relationship_breadth distinct counterparties
          × task_performance     win rate over resolved journal outcomes
          × recency_weight       time since the last meaningful write
```

Every factor is clamped, computed in exact decimal, and reports its own inputs
and a sentence explaining what it did with them. It prices only what is actually
for sale — a record marked non-transferable does not lift the figure.

**Not built, deliberately:** no `buyer_demand`, `origin_reputation`, or
`buyer_satisfaction` term, and no memory-reputation score. Those are real inputs
at protocol scale and meaningless in a single-listing demo. A hardcoded "12
buyers watching" is exactly the smoke-and-mirrors pattern a technical judge
probes first. Demand-based pricing arrives with real transaction volume.

---

## Privacy and redaction

Two independent axes, not collapsed into one:

- **`sensitivity`** — `public` (visible in the pre-purchase data room),
  `private` (transfers with the sale, never previewed), or
  `redacted-preview-only`.
- **`transferable`** — `false` is absolute. It outranks every tier, every buyer,
  and every category selection, permanently.

Filtering runs **before hashing**, not before display, so a withheld record never
reaches the Merkle tree in recoverable form. The data room is constructed from
counts, so there is no body in scope to leak by accident, and its test sweeps the
entire serialized preview against every private string in the tenant.

An unflagged record defaults to `private` and `transferable` — part of the asset,
but not leaking into a preview because nobody remembered to flag it.

**The honest caveat:** relationship entities describe real counterparties, and a
production version needs an actual answer to "under what terms can this data move
with a sale", grounded in the operator's own terms of service with its end users.
That is a genuine unresolved legal question a hackathon build should not pretend
to solve. All demo memory uses invented personas; no real personal data appears
anywhere in this project, including in local test fixtures.

---

## Sealing

What stops the seller from keeping a copy and carrying on?

1. **Contract-level.** `confirmTransfer` sets a `sealed` flag against the
   `agentId`, readable by the ACP registry or any future buyer. A sealed agent
   cannot be relisted.
2. **Memory-service-level.** The seller's credentials for that tenant are
   revoked, and every write path — the adapter *and* the underlying
   `MemoryClient` — checks the seal first and rejects unconditionally.

There is deliberately no `unseal`. Un-sealing would recreate the exact state the
seal exists to prevent, and an admin escape hatch is the same hole with a login
page in front of it.

**What sealing does not claim:** the seller's database file still exists on their
disk, and nothing here reaches onto their machine. What it guarantees is
narrower and actually enforceable — that copy can no longer authenticate, sync,
or be represented anywhere in this system as the live agent. The asset was never
the bytes; it was the right to *be* that agent.

---

## The lifecycle model

Selling outright is one instance of a broader lifecycle.

| Primitive | Mechanism | Status |
|---|---|---|
| **Sell** | Full or partial transfer, permanent, against payment | **Built** |
| **Partial succession** | The same pipeline with a category filter before serialization, verified against the per-category subroots | **Built** |
| **Archive** | Freeze a tenant without transferring it | **Free** — Sibyl's own `archive_entity` semantics at tenant level |
| **Lease** | Sell, plus a time-boxed re-seal timer on the buyer's copy | Designed, not built — a second time-based subsystem |
| **Conditional** | Category-filtered pipeline gated by an oracle-style condition before the key is released | Designed, not built |
| **Inherit** | The same pipeline, different trigger, no payment leg | Roadmap |
| **Merge** | Combine two tenants with a conflict rule for overlapping `(category, name)` keys | Roadmap — merging two independently-evolved memories safely is its own project |
| **Split** | Partition one tenant along a category boundary | Roadmap — the inverse of merge; reuses the category filtering |
| **Revoke** | Invalidate a buyer's future access under a lease | Roadmap — depends on lease existing first |

The import pipeline refuses to write into a non-empty tenant precisely because
merge is not built: silently colliding on the uniqueness constraint is not a
merge, it is data loss with a friendly error message.

---

## Known limits, stated rather than hidden

- **The buyer asserts the delivered hash.** A dishonest buyer can submit a wrong
  hash, take the automatic refund, and keep the decrypted package. No on-chain
  logic can close this, because the chain cannot see the delivered bytes. The
  contract's `arbiter` role is the designed answer — the hook for an
  Evaluator-style third-party agent, borrowing the trust pattern ACP already uses
  for job quality. Wiring a real evaluator into it is roadmap; the role exists now
  so the contract does not need redeploying to gain one.
- **Atomicity is by ordering, not by magic.** A single transaction cannot span
  the chain and an off-chain store. `confirmTransfer` is genuinely atomic because
  it is one EVM transaction; the delivery and the seal are ordered around it so
  every intermediate state is safe to abandon.
- **`relationships/` carries the WARM edges**, so its subroot depends on which
  other categories travel with it — an edge is pruned when the entity at its far
  end is not part of the sale. A partial sale therefore commits its own root.
- **`LocalSettlement` is not the contract.** It mirrors the state machine so the
  pipeline can be exercised without a funded wallet. Substituting it for the
  chain in a demo would be exactly the dishonesty this project exists to avoid.
- **Testnet deployment, ACP service-registry registration, and the two-machine
  rehearsal are not done here** — they need funded wallets and two hosts. The
  contract compiles and its bytecode is executed against 23 EVM tests; the
  Foundry suite mirrors them for a machine with `forge`.

## Drift from the build spec, found while building

- The free tier caps a store at **5 MB** (`FREE_TIER_CAP_BYTES`), not the 2 MB
  the spec quotes.
- `list_entities(category=…)` exists natively; there is no need to iterate
  `search_entities` with an empty query.
- Listing calls clamp `limit` to 10,000, so a full export pages rather than
  asking for everything at once.
- `get_state` / `get_reference` are keyed-only, so enumerating those two tiers
  for a full export goes through the client's documented `storage` escape hatch.
  Writes always return through the public API so the cap gate and FTS triggers
  still run.

## Deployment

The UI deploys to Netlify from `netlify.toml` (base `web/`, publish `web/dist`).

The Netlify project is **`succession-memory`**
(`app.netlify.com/projects/succession-memory`, site id
`8518ba9f-c4cd-464a-b415-eb7ef6d2284a`). Link this repository to it under
**Site configuration → Build & deploy → Continuous deployment**, branch
`claude/session-3993th`; `netlify.toml` supplies the build settings, so nothing
needs configuring in the UI.

The pipeline is Python and does **not** deploy there — Netlify's function
runtimes will not run FastAPI. Deploy `service/` to any always-on host
(Railway, Render, Fly.io) and uncomment the `/api/*` proxy in `netlify.toml` to
point the UI at it. Proxying through the same origin also means the service
needs no CORS grant for the Netlify domain.

With no service reachable, the hosted build runs in **recorded mode**: it
replays `web/public/recorded-run.json`, the captured output of one real
end-to-end run. Every hash, signature, agent reply, and the rejected write
against the sealed tenant in that file is genuine output, and the root is
reproducible — `python -m succession.demo` prints the same one, because the
export is deterministic. A banner names the mode and the recording date on
every screen; a recorded run presented as a live one is exactly the pattern
this project argues against. Regenerate the artifact whenever the pipeline
changes.

## Prior work

Everything in this repository was written for this hackathon. Third-party
dependencies are the ones named in the build spec: `sibyl-memory-client`,
`eth-account`, `pycryptodome`, and the standard React/Vite/Tailwind frontend
stack. `ListingContract.sol` is original; the ERC-20 and ERC-721 interfaces it
imports are the standard minimal subsets.
