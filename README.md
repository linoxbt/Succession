<div align="center">

<img src="web/public/favicon.svg" width="72" height="72" alt="Succession" />

# Succession

**The property layer for agent memory.**

Agent memory becomes a transferable asset — exported into a signed portable
package, committed to a hash before a buyer exists, settled atomically on Base
after independent evaluation, and verified again from the buyer's own store.

[Overview](#overview) · [How it works](#how-a-sale-works) · [Quick start](#quick-start) ·
[Architecture](#architecture) · [Security](#security-model) · [Roadmap](docs/ROADMAP.md)

`Python 3.11+` · `Solidity 0.8.28` · `React 18`

</div>

---

## Current audit status

The September 2026 remediation and coordinated Base Sepolia release are complete
for the tested EOA flow. [AUDIT_STATUS.md](docs/AUDIT_STATUS.md) records verified
fixes and remaining limits; [release acceptance](docs/RELEASE_ACCEPTANCE_2026-09-09.md)
records the live transactions and hosted restart recovery. This is testnet pilot
evidence, not a mainnet or third-party audit certification.

## Overview

Code gives an agent capability. A model gives it reasoning. Memory gives it
continuity — and Succession gives that continuity an economic life beyond the
original agent.

The code can be replaced. The model can be replaced. The wallet can be replaced.
The accumulated relationships, preferences, history and context are what
actually can't be.

> The model and the code are the employee. The accumulated memory is the
> customer book — the relationships, preferences and institutional knowledge
> that make an operating business worth more than its equipment. **Succession
> does not sell the employee. It makes the customer book itself a transferable
> asset.**

### Why this is hard to fake

Anyone can build a UI that says *transfer complete*. Five things here make the
claim checkable instead:

| | |
|---|---|
| **The commitment precedes the buyer** | The Merkle root is posted at listing time, so it cannot be computed after the fact to match whatever was delivered. |
| **Verification re-hashes the destination** | Checking the bytes received only proves the courier was honest. Re-exporting the buyer's own store proves the importer wrote what it received and the engine did not silently coerce anything. |
| **The signature covers the whole header** | Signing only the root would leave the agent identity and owner chain unauthenticated — an intercepted package could keep a valid signature while claiming to be a different, more valuable agent. |
| **Two genuinely separate stores** | Seller and buyer get their own SQLite files in every test. Two browser tabs on one database would pass a demo and fail the suite. |
| **The seller's tenant is retired** | The contract records the handover atomically; the seller watcher then applies a durable local write seal through the supported adapter. |

---

## How a sale works

```
   seller tenant                                                buyer tenant
        │                                                            ▲
        │  1. filter → serialize → hash → sign                       │
        ▼                                                            │
   SMP package ──── 2. commit root ────▶  ListingContract (Base)      │
        │                                        │                   │
        │                            3. buyer funds escrow           │
        │                                        │                   │
        └── 4. AES-256-GCM envelope, key released on escrow ─────────┘
                                                 │           5. import + RE-HASH
                                                 ▼                   │
                              6. confirmTransfer(deliveredRoot) ◀─────┘
                                 ├─ release payment to seller
                                 ├─ transfer ERC-8004 identity
                                 └─ set sealed flag     ── all three, or none
```

**Atomicity is by ordering, not by magic.** A single transaction cannot span an
EVM chain and an off-chain store, and any design claiming otherwise is hiding a
failure mode. Step 6 is genuinely atomic because it is one EVM transaction;
steps 4–5 and the local seal use separate recovery records. A failed import rolls
back its writes without deleting pre-existing memory. A chain refund requires
a refund transaction or expiry recovery; a local failure does not itself move
funds. Delivery before payment still permits a buyer to retain plaintext and
refund. That unresolved policy is a release blocker.

---

## Quick start

```bash
pipx install "succession-cli[chain,mcp]"

succession                     # the wordmark, then a guide to everything below
succession status              # what this install is connected to
succession audit               # check every claim this project makes
succession market --marketplace https://succession-production-7320.up.railway.app
```

`succession audit` is the one to run first if you are evaluating this. It needs
no repository, no wallet and no network: it builds a memory, sells it to itself,
and measures seven claims, exiting non-zero if any fails. Add `--check-chain`
and it additionally compares every published Merkle root to its commitment on
Base.

Set these once and the rest of the commands stop needing flags:

```bash
export SUCCESSION_MARKETPLACE=https://succession-production-7320.up.railway.app
export BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
```

### Selling, step by step

Listing happens on the seller's machine, and has to. Sibyl 0.8.0 is local-only:
`MemoryClient.local(path)` is its sole constructor and the SDK's entire network
surface is a capacity check and a heartbeat carrying an integer, so a store is a
SQLite file on its owner's disk and no web page can read it. That constraint is
also the only arrangement in which "plaintext never leaves the seller before
escrow" is a fact rather than a promise: the export, the encryption and the
signature all happen locally, and what reaches the network is a hash, a
signature, aggregate counts and ciphertext.

```bash
export SUCCESSION_SIGNING_KEY=0x…          # never passed as an argument

# 1. What is actually sellable, per directory, split by what consent withholds.
succession inventory --db ~/.sibyl-memory/memory.db --tenant my-agent

# 2. Prove a sale would carry every directory intact, before committing to one.
#    Exports, imports into a throwaway store, re-exports, compares subroots.
succession prove --db ~/.sibyl-memory/memory.db --tenant my-agent \
  --agent erc8004:84532:0417

# 3. Commit the root on Base and publish the data room and ciphertext.
succession list --db ~/.sibyl-memory/memory.db --tenant my-agent \
  --agent erc8004:84532:0417 --price 25000000      # 25 USDC, 6 decimals

# 4. Release the content key when, and only when, escrow is funded on chain.
succession fulfil
```

Selling part of an agent takes `--scope`, which is a percentage per directory:

```bash
succession list … --scope relationships=60,history=100,preferences=100
```

Records are ordered newest first and a percentage takes that many from the
front, so a successor inherits recent context rather than the oldest half.
Relationship edges follow their endpoints rather than counting toward the
percentage, because half an edge is not a thing.

If the marketplace was unreachable when you listed, the commitment still stands
and the vault still holds the package. Re-running `list` would try to list the
same agent twice and the contract would refuse, so publish separately:

```bash
succession publish --listing listing-…
```

### Buying and evaluation, step by step

```bash
export SUCCESSION_BUYER_KEY=0x…            # a different wallet to the seller's

succession market                          # what is for sale
succession show --listing listing-…        # the data room, before paying

# Funding escrow sends real transactions. Without --yes this describes
# the two transactions it would send and stops.
succession buy --listing listing-… --yes

# The independent evaluator receives the key, imports into an isolated store,
# checks the seller signature, re-derives the root, and settles on its verdict.
export SUCCESSION_EVALUATOR_KEY=0x…
succession evaluate --listing listing-… --db evaluator.db --tenant isolated --yes

# Only after evaluator settlement can the buyer collect, decrypt, and import.
succession claim --listing listing-… --db buyer.db --tenant my-successor
```

### Working from a checkout instead

```bash
git clone https://github.com/linoxbt/Succession && cd Succession

python -m venv .venv
.venv/bin/pip install -e "packages/succession[test,service,acp,chain,mcp]"
( cd contracts && npm install && npm run build )            # solc → artifacts
.venv/bin/python -m pytest packages/succession/tests

PYTHONPATH=. .venv/bin/uvicorn service.app:app --port 8000  # API
( cd web && npm install && npm run dev )                    # UI on :5173
```

### For an agent rather than a person

```bash
pipx install "succession-cli[chain,mcp]"
succession-mcp
```

The MCP server offers dedicated inspection, pricing, verification and sale
tools, plus `run_command` for every CLI command. `quote` applies remembered
margin-floor and opening-premium rules to explicit amounts; it sends no quote
to a counterparty. Commands that write files, publish, release keys or transact
require `SUCCESSION_MCP_ALLOW_WRITES=1`. Signing keys come from the operator's
environment; tools do not request them. Command output and failures are returned
from isolated subprocesses. See [operations](docs/OPERATIONS.md) for wallet
authorization and local retirement limits.

## Commands

<!-- BEGIN GENERATED COMMANDS -->

<!-- Written by scripts/generate_reference.py from the argparse
     parsers themselves. Do not edit by hand: CI regenerates this
     block and fails on a diff. -->

### Start here

Nothing here changes anything.

```bash
succession status                                         # what this installation is connected to
succession audit                                          # check every claim this project makes about itself
succession market                                         # what is for sale
succession show --listing …                               # one listing's data room, before paying
```

### Selling

Runs on your own machine, against your own store.

```bash
succession inventory --db … --tenant …                    # what this agent actually has to sell, per category
succession value --db … --tenant …                        # compute the reference valuation
succession preview --db … --tenant … --agent …            # compute the data-room preview
succession prove --db … --tenant … --agent …              # prove every category transfers, against your own store
succession export --db … --tenant … --agent … --out …     # build and sign an SMP package
succession list --db … --tenant … --agent … --price …     # list your agent's memory for sale, on chain
succession publish --listing …                            # publish an already-listed agent to a marketplace
succession fulfil                                         # release content keys once escrow is funded
succession listings                                       # what you have listed
```

### Buying

Fund escrow, then claim after independent evaluator settlement.

```bash
succession buy --listing …                                # fund escrow for a listing
succession claim --db … --tenant … --listing …            # collect, import and verify memory you bought
```

### Evaluating

Import into an isolated tenant, verify, and settle on the evaluator's signed verdict.

```bash
succession evaluate --db … --tenant … --listing …         # independently verify and settle an escrowed delivery
```

### Compatibility

Retained to explain the evaluator migration to older buyer scripts.

```bash
succession confirm --listing … --root …                   # deprecated: buyers cannot settle delivery
```

### Working with a package directly

For inspecting a file you were handed.

```bash
succession inspect package                                # describe a package without importing it
succession verify package --root … --signer …             # check a package against a commitment
succession import package --db … --tenant … --root … --signer …# import a package into a fresh tenant
```

### Virtuals ACP

```bash
succession-acp status                                     # confirm registration and show job history
succession-acp sync                                       # mirror ACP job history into a tenant's memory
succession-acp snapshot                                   # capture live job history to a file
succession-acp show                                       # show the job history a tenant already carries
```

### Environment

| Variable | What it is for |
|---|---|
| `SUCCESSION_SIGNING_KEY` | The seller's wallet. Read from the environment, never an argument, because a private key on a command line lands in shell history and in the process table. |
| `SUCCESSION_BUYER_KEY` | The buyer's wallet. Deliberately a different variable from the seller's: conflating them is how someone tries to buy their own listing. |
| `SUCCESSION_EVALUATOR_KEY` | The independent evaluator wallet configured in the listing contract. It alone may settle a delivery. |
| `SUCCESSION_FINALITY_CONFIRMATIONS` | Receipt depth required before a chain write is accepted. Defaults to three on Base Sepolia and one on local EVMs. |
| `SUCCESSION_MARKETPLACE` | Which marketplace to publish to and read from. Defaults to http://127.0.0.1:8000, which is right for local development and wrong for everything else. |
| `BASE_SEPOLIA_RPC_URL` | How to reach the chain. |
| `SUCCESSION_DEPLOYMENT` | Path to the deployment record. The packaged copy is used when this is unset and no checkout is present. |
| `SUCCESSION_ARTIFACTS` | Path to the contract ABI. Same fallback as the deployment record. |
| `SUCCESSION_VAULT` | Where the seller's listings, envelopes and content keys are kept. Defaults to ~/.succession/listings. |
| `SUCCESSION_MCP_ALLOW_WRITES` | Set to 1 to let an MCP client call the tools that spend money, release a decryption key, or permanently seal an agent. Off by default because sealing has no undo. |
| `SIBYL_CREDENTIALS` | Path to credentials.json. Without it the memory SDK enforces a strict 5 MB cap and the paid features gate off. |

<!-- END GENERATED COMMANDS -->

## Architecture

```
packages/succession/src/succession/
├── canonical.py     deterministic serialization — the basis of every hash
├── merkle.py        two-level Merkle tree, per-category subroots
├── smp.py           the nine-directory package format
├── redaction.py     sensitivity flags and transferability
├── export.py        filter → serialize → hash → sign
├── importer.py      verify → re-key → re-hash the destination
├── provenance.py    the signed header and the owner chain
├── envelope.py      AES-256-GCM delivery, key escrowed with payment
├── settlement.py    the SettlementBackend interface + local mirror
├── chain.py         the same interface, over web3, against Base
├── erc8004.py       identity: registration, the agent file, transfer
├── evaluator.py     the arbiter that re-derives instead of trusting
├── acp.py           Virtuals ACP job history
├── valuation.py     five clamped factors, exact decimal
├── dataroom.py      aggregate-only preview
├── seal.py          the seal registry and write guard
├── certificate.py   the Succession Certificate
├── publish.py       the seller's side: list your own store, keep the key
├── fulfil.py        release the key, only against escrow read from chain
├── transfer.py      the orchestrator
├── agent.py         retrieval over Sibyl's FTS index
├── catalog.py       the marketplace population — several distinct agents
└── memory/          the engine adapter — Sibyl is the reference implementation

contracts/src/ListingContract.sol    escrow, atomic settlement, the sealed flag
                                     one live listing per agent; cancel before escrow
scripts/                             deploy, run N transfers, record a run
service/app.py                       the marketplace: chain-backed, no seed data
service/registry.py                  metadata the contract has no field for
service/walkthrough.py               the sample-agent walkthrough, quarantined
web/                                 landing page and operations console
web/src/dash/                        read-only dashboard, guide and video runbook
```

### The memory package

Nine directories — six carry memory, three are generated and describe the
package:

| Directory | Carries |
|---|---|
| `identity/` | The agent's own registration record |
| `relationships/` | Per-counterparty entities, and the WARM edges between them |
| `preferences/` | Learned settings and operating limits |
| `history/` | The COLD journal, ARCHIVE records, verifiable ACP job history |
| `commitments/` | Open quotes, agreed terms, and HOT working state |
| `learned-behaviors/` | Adapted patterns and REFERENCE playbooks |
| `provenance/` | Origin, version, prior-owner chain, signature |
| `permissions/` | Redaction flags, consent basis, access tiers |
| `integrity-proof/` | Merkle root and per-category subroots |

A directory is a **selection unit**, not a storage location — it is what partial
succession filters on and what gets its own subroot. Every record also carries
its `origin`, the exact tier and category it held in the source engine, which is
what the importer re-keys against. The grouping can be opinionated without ever
being lossy.

Full specification: [`docs/smp-format.md`](docs/smp-format.md).

### The integrity scheme

Two-level Merkle tree over keccak256 with RFC 6962 domain separation.

| Decision | Why |
|---|---|
| Leaves and internal nodes are prefixed differently | Blocks the second-preimage attack where a node is presented as a leaf |
| An odd node is promoted, never duplicated | Duplication makes two different leaf multisets share a root |
| The category name is bound to its subroot | A cheap directory cannot be relabelled as an expensive one |
| Row ids and destination timestamps are excluded from leaves | Hashing them would make every honest import fail verification |
| Ties break on content hash, not row id | Row ids do not survive a transfer |

The two-level shape is what makes partial succession verifiable without a
redesign. A flat hash would have needed one.

### The marketplace

The index is the chain. `Listed` events decide what exists and the contract
decides each listing's state, price and seller; this service only adds what the
contract has no field for — the data-room counts, the reference valuation, the
display name — and every one of those rows is signed by the address the contract
records as that listing's seller.

That is a change from an earlier build, which shipped six seeded archetypes.
They are gone. A listing appears here because someone paid gas to commit its
root, so an empty marketplace is a true answer rather than a broken fetch.

Alongside the real listings the console shows a small set of clearly labelled
demonstration rows, so the interface can be judged at a realistic size while the
live market is small. They travel in their own API field rather than mixed into
`listings`, their seller is the zero address, and no total, volume or capability
count includes them. A test asserts exactly that.

### Valuation

```
valuation = base_price
          × tenure_factor        age of the tenant
          × interaction_density  journal events per day over that tenure
          × relationship_breadth distinct counterparties
          × task_performance     ACP settlement outcomes, else the journal
          × recency_weight       time since the last meaningful write
```

Exact decimal, every factor clamped, every factor reports its own inputs and a
sentence explaining what it did with them. It prices only what is for sale — a
record marked non-transferable does not lift the figure.

**Deliberately absent:** no `buyer_demand`, `origin_reputation` or
`buyer_satisfaction` term. A separate memory-reputation calculation exists, but
seller-provided lineage and history are explicitly unverified. The model does
not turn self-reported history into independently established reputation.

---

## Partner stacks

| Stack | Where it does work | Status |
|---|---|---|
| **Sibyl Memory** | The asset itself. Five tiers export, hash, transfer and re-key; the successor agent retrieves through the FTS5 index. Delete this layer and there is no product. | Executed |
| **Base** | `ListingContract.sol` holds escrow and, in one transaction, releases payment, transfers the ERC-8004 identity and sets the sealed flag. `chain.py` drives seller, evaluator and buyer transactions from their separate operator environments. Identity is a real ERC-8004 registry on Base Sepolia (`0x7177a686…36Dd09A`), verified on chain rather than assumed, and payment moves in Circle's USDC. | **Deployed to Base Sepolia** at `0x642dFC05C9DCC0617c67B318C78dd5AE94134603`, with 5 initial acceptance sales (4 verified, 1 deliberate evaluator refund), a hosted restart-recovery sale, and a verified video-demo sale. |
| **Virtuals ACP** | `acp.py` reads job history through `virtuals-acp` and makes it the data room's quality-of-earnings signal, the valuation's `task_performance` input, and part of the transferred memory. | Built. **Not yet registered** — needs a whitelisted wallet and entity id. |

The current release verified the registry, exact deployment input, evaluator,
EOA funding/claim flow, service restart recovery and buyer journal recovery.
External Virtuals ACP jobs remain. The current web dashboard is read-only; wallet
transactions use the role-specific CLI environments accepted in the live EOA flow.
See [audit status](docs/AUDIT_STATUS.md) for the evidence and release gates.

```bash
# Finish both. Preflights keys, RPC reachability and wallet balances first.
./scripts/finish_integrations.sh
```

---

## Security model

### Privacy and redaction

Two independent axes, not collapsed into one:

- **`sensitivity`** — `public` (visible pre-purchase), `private` (transfers,
  never previewed), `redacted-preview-only` (counts, body withheld).
- **`transferable`** — `false` is absolute. It outranks every tier, buyer and
  category selection, permanently.

Filtering runs **before hashing**, not before display, so a withheld record
never reaches the Merkle tree in recoverable form. The data room is constructed
from counts, so there is no body in scope to leak by accident, and its test
sweeps the entire serialized preview against every private string in the tenant.

An unflagged record defaults to `private` and `transferable` — part of the
asset, but not leaking into a preview because nobody remembered to flag it.

### Sealing

Confirmation transfers the NFT and payment atomically on chain and records the
former owner. The new owner can sell the identity again with a new listing.
After observing confirmation, the seller watcher retires the source tenant in
its local database. Every write through a Succession-opened Sibyl client checks
that seal inside the write transaction, including reopened clients.

This is cooperative local retirement. It does not revoke remote Sibyl account
credentials, destroy files, or prevent a file owner from bypassing the adapter.
The certificate leaves the seller's local seal timestamp empty unless actually
observed. Memory scope filters do not divide the identity token: a partial
memory sale still transfers the whole NFT.

### Known limits

- **Delivery-before-payment permits plaintext retention and refund.** The buyer
  can read memory and subsequently refund or let escrow expire. An optional
  evaluator does not prevent this. Mandatory evaluator settlement before buyer
  key release would change the business flow and remains an open product
  decision. Do not treat the current contract as trustless information escrow.
- **`relationships/` carries the WARM edges**, so its subroot depends on which
  other categories travel with it — an edge is pruned when the entity at its far
  end is not part of the sale. A partial sale therefore commits its own root.
- **`LocalSettlement` is not the contract.** It mirrors the state machine so the
  pipeline runs without a funded wallet. Substituting it for the chain in a demo
  would be exactly the dishonesty this project exists to avoid.
- **API authentication is per request.** Metadata and key release require a
  seller signature binding method, path, raw body, chain, contract, expiry and
  nonce. Key collection requires the escrow buyer's signature. Public aggregate
  reads and encrypted envelopes require no signature. The admin token applies
  only to operational routes. Walkthrough sessions are isolated synthetic demos.

- **Counterparty data is a real legal question.** Relationship records describe
  real people and companies, and a production version needs an actual answer to
  what terms let that data move with a sale, grounded in the operator's own
  terms of service. A hackathon build should not pretend to solve it.

---

## Testing

```bash
.venv/bin/python -m pytest packages/succession/tests
( cd contracts && forge test )
```

| Suite | Covers |
|---|---|
| `test_roundtrip` | Export → import → re-hash; determinism; five corruption and forgery cases |
| `test_merkle` | Domain separation, odd-node promotion, category binding, canonicalization |
| `test_partial` | Category filtering, subroot proofs, edge pruning |
| `test_seal` | Every write path gated; sealing is permanent and idempotent |
| `test_dataroom` | The preview swept against every private string in the tenant |
| `test_transfer` | Both refund paths; nothing half-written; the envelope |
| `test_contract` | 27 tests against real compiled bytecode in py-evm |
| `test_chain_transfer` | The whole pipeline settled on chain |
| `test_acp` | Job history maths, memory sync, the valuation switch, the registration gate |
| `test_agent` | Recall by name, by lane, and after a transfer |
| `test_cli` | Export and import as separate processes |
| `test_service` | The HTTP layer, end to end |
| `test_erc8004` | The registration file, the identity string, and the live registry |
| `test_evaluator` | Independent re-derivation, and the theft the contract cannot stop alone |

Foundry is the contract toolchain; where `forge` cannot be installed,
`contracts/compile.js` drives solc and the Python suite executes the same
compiled bytecode. The Python suite rebuilds the artifacts itself when a `.sol`
file is newer than the last build, so a stale `contracts/out` cannot make the
contract look broken.

The two suites overlap heavily but are not identical, and it is worth being
precise about that rather than claiming a parity that does not hold. Foundry
alone covers a fee-taking token, escrow isolation between listings, and a fuzz
case over the delivered hash; py-evm alone covers a token that returns false
rather than reverting, a double purchase, and the registration URI carried by
the identity. They are worth keeping that way: the Foundry suite catches what
only a cheatcode can reach, and the py-evm suite is what runs where Foundry
cannot be installed.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/smp-format.md`](docs/smp-format.md) | The package format as a specification another engine could implement |
| [`docs/sibyl-setup.md`](docs/sibyl-setup.md) | Sibyl Pro setup, the memory walkthrough, primitives used |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Everything remaining to be production-ready |
| [`docs/RELEASE_ACCEPTANCE_2026-09-09.md`](docs/RELEASE_ACCEPTANCE_2026-09-09.md) | Live deployment, transaction and two-host recovery evidence |
| [`docs/INDEPENDENT_CONTRACT_REVIEW_2026-09-09.md`](docs/INDEPENDENT_CONTRACT_REVIEW_2026-09-09.md) | Slither/manual contract review and its assurance boundary |
| [`docs/VIDEO_DEMO_SCRIPT.md`](docs/VIDEO_DEMO_SCRIPT.md) | Timed narration and terminal commands for the release video |
| In-app **Guide** | Role-separated operation and a copyable terminal checklist |

---

## Prior work

Everything in this repository was written for the Sibyl Labs Hackathon
(1–10 September 2026). Third-party dependencies are `sibyl-memory-client`,
`virtuals-acp`, `eth-account`, `web3`, `pycryptodome`, and the React/Vite/
Tailwind frontend stack. `ListingContract.sol` is original; the ERC-20 and
ERC-721 interfaces it imports are the standard minimal subsets.

All counterparties, companies and figures in the seeded memory are invented. No
real personal data appears anywhere in this project, including in local test
fixtures.
