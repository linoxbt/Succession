<div align="center">

<img src="web/public/favicon.svg" width="72" height="72" alt="Succession" />

# Succession

**The property layer for agent memory.**

Agent memory becomes a transferable asset — exported into a signed portable
package, committed to a hash before a buyer exists, settled atomically on Base,
and verified by the buyer re-hashing their own store.

[Overview](#overview) · [How it works](#how-a-sale-works) · [Quick start](#quick-start) ·
[Architecture](#architecture) · [Security](#security-model) · [Roadmap](docs/ROADMAP.md)

`259 tests` · `Python 3.11+` · `Solidity 0.8.28` · `React 18`

</div>

---

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
| **The seller's copy is sealed** | At the contract level and the service level, the instant escrow releases. |

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
steps 4–5 and the seal are ordered around it so every intermediate state is safe
to abandon. A failure before settlement refunds the buyer, purges their
half-written tenant, and leaves the seller exactly as they were.

---

## Quick start

```bash
git clone https://github.com/linoxbt/Succession && cd Succession

python -m venv .venv
.venv/bin/pip install -e "packages/succession[test,service,acp,chain]"
.venv/bin/python -m pytest packages/succession/tests        # 259 tests

( cd contracts && npm install && npm run build )            # solc → artifacts
.venv/bin/python -m succession.demo                         # the whole workflow

PYTHONPATH=. .venv/bin/uvicorn service.app:app --port 8000  # API
( cd web && npm install && npm run dev )                    # UI on :5173
```

### Selling your own agent's memory

Listing happens on the seller's machine, and has to. Sibyl 0.8.0 is local-only —
`MemoryClient.local(path)` is its sole constructor and the package makes no
network calls beyond a tier check — so a store is a SQLite file on its owner's
disk and no web page can read it. That constraint is also the only arrangement
in which "plaintext never leaves the seller before escrow" is a fact: the
export, the encryption and the signature all happen locally, and what reaches
the network is a hash, a signature, aggregate counts and ciphertext.

```bash
# 1. Commit your memory's root on chain and keep the key in a local vault.
SUCCESSION_SIGNING_KEY=0x… succession list \
  --db ~/.sibyl-memory/memory.db --tenant my-agent \
  --agent erc8004:84532:417 --price 25000000        # 25 USDC, 6 decimals

# 2. Release the content key when — and only when — escrow is funded on chain.
succession fulfil

# 3. Buyer side: collect, import into your own store, and re-hash it there.
succession claim --listing listing-… --db buyer.db --tenant my-successor
```

`succession list` refuses to run without a deployment record. Listing settles on
chain and there is deliberately no offline mode for it: `LocalSettlement`
mirrors the contract's state machine closely enough that a seller could watch
every screen say "listed" while nothing had touched a chain.

### The rest of the command line

```bash
succession export  --db seller.db --tenant t-seller --agent erc8004:84532:0417 --out pkg
succession verify  pkg --root 0x… --signer 0x…
succession import  pkg --db buyer.db --tenant t-buyer --root 0x… --signer 0x…
succession value   --db seller.db --tenant t-seller
succession preview --db seller.db --tenant t-seller --agent erc8004:84532:0417
succession listings                                  # what you have listed

succession-acp status
succession-acp sync --db seller.db --tenant t-seller
```

Export writes a package to disk; verify and import read it back in separate
invocations against a separate store. That is deliberately the path a
two-machine transfer takes — nothing is passed in memory between the halves.

### What is in the app, and what is not

The **Marketplace** shows only listings that exist on chain. There is no seed
data and no cached recording behind it — an empty marketplace means nobody has
listed yet, and that is the answer it gives.

The **Walkthrough** is a scripted sale on a sample agent, kept in its own module
(`service/walkthrough.py`), under its own route prefix, settling through
`LocalSettlement`, with every response stamped `simulated: true` and a banner
that does not go away. It exists because the load-bearing claim — that a
successor agent inherits working context rather than a file — is only
convincing when you watch a cold agent answer from memory it did not have a
minute ago. No code path connects it to the marketplace.

---

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
web/src/chain/                       wallet connection and on-chain escrow
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

Six listings, each a real export of a real store. The committed root, record
count, memory size and valuation are computed by the pipeline — nothing on that
screen is written down. A marketplace of hardcoded rows would look identical and
mean nothing, which is exactly the pattern this project argues against.

The archetypes differ along the axes the valuation reads — tenure, journal
density, counterparty breadth, win rate, recency — so the spread of prices comes
out of the data rather than out of a designer's sense of what looks good. One is
deliberately stale and one deliberately has too few resolved outcomes to score,
because a market where every listing looks healthy teaches a buyer nothing.

Asking prices are derived as a ratio of each agent's own valuation, so the two
can never contradict each other, and the resulting spread (−12% to +18%) is a
real signal a buyer can sort on.

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
`buyer_satisfaction` term, and no memory-reputation score. Those are real inputs
at protocol scale and meaningless in a single-listing demo. A hardcoded "12
buyers watching" is exactly the pattern a technical reader probes first.

---

## Partner stacks

| Stack | Where it does work | Status |
|---|---|---|
| **Sibyl Memory** | The asset itself. Five tiers export, hash, transfer and re-key; the successor agent retrieves through the FTS5 index. Delete this layer and there is no product. | Executed |
| **Base** | `ListingContract.sol` holds escrow and, in one transaction, releases payment, transfers the ERC-8004 identity and sets the sealed flag. `chain.py` drives it over web3; the browser funds escrow through Wagmi and the Base Account connector. Identity is a real ERC-8004 registry on Base Sepolia (`0x7177a686…36Dd09A`), verified on chain rather than assumed, and payment moves in Circle's USDC. | Built; contract executed against real bytecode in py-evm, registry verified live. **Not yet deployed to Base Sepolia** — needs a funded key. |
| **Virtuals ACP** | `acp.py` reads job history through `virtuals-acp` and makes it the data room's quality-of-earnings signal, the valuation's `task_performance` input, and part of the transferred memory. | Built. **Not yet registered** — needs a whitelisted wallet and entity id. |

Base Sepolia and `acpx.virtuals.gg` are both reachable now, and the ERC-8004
registry above was verified against the live chain — `test_erc8004.py` re-checks
it on every run and skips rather than fails when the network is not there. What
is still missing is a **funded deployer key** and **ACP credentials**, neither of
which is a code path. Everything that does not need money or a whitelist is
done; the deploy script refuses to build on an address that holds no code, so it
cannot quietly succeed against nothing.

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

1. **Contract-level.** `confirmTransfer` sets a `sealed` flag against the
   `agentId`. A sealed agent cannot be relisted.
2. **Service-level.** Credentials for that tenant are revoked, and every write
   path — the adapter *and* the underlying `MemoryClient` — checks the seal
   first and rejects unconditionally.

There is deliberately no `unseal`. It would recreate exactly the state the seal
prevents, and an admin escape hatch is the same hole with a login page.

**What sealing does not claim:** the seller's database file still exists on
their disk, and nothing reaches onto their machine. The guarantee is narrower
and actually enforceable — that copy can no longer authenticate, sync, or be
represented anywhere in this system as the live agent. The asset was never the
bytes; it was the right to *be* that agent.

### Known limits

- **The buyer asserts the delivered hash — unless an Evaluator settles.** Left
  to the buyer, a dishonest one can submit a wrong root, take the automatic
  refund, and keep the decrypted package; no on-chain logic closes that, because
  the chain cannot see the delivered bytes. `evaluator.py` is the third party
  that does: it is handed the buyer's *store*, not a number, re-runs the export
  pipeline over it, and settles as the contract's `arbiter` with the root it
  derived itself. Receipts record which of the two confirmed, so the weaker
  evidence never reads as the stronger one. What remains open is that the buyer
  can refuse the evaluator access — in which case nobody is paid and the escrow
  expires back to them, which is the right outcome rather than a silent one.
- **`relationships/` carries the WARM edges**, so its subroot depends on which
  other categories travel with it — an edge is pruned when the entity at its far
  end is not part of the sale. A partial sale therefore commits its own root.
- **`LocalSettlement` is not the contract.** It mirrors the state machine so the
  pipeline runs without a funded wallet. Substituting it for the chain in a demo
  would be exactly the dishonesty this project exists to avoid.
- **The service gates writes, and that is all it gates.** With
  `SUCCESSION_API_TOKEN` set, every mutating route needs a bearer token; unset,
  it accepts writes from localhost and refuses them from anywhere else. Reads —
  the data room, the marketplace — stay open, because they are meant to be. This
  is an access gate, not accounts: there is still no notion of a *user*, which
  is a P1 item and not a solved problem.
- **Counterparty data is a real legal question.** Relationship records describe
  real people and companies, and a production version needs an actual answer to
  what terms let that data move with a sale, grounded in the operator's own
  terms of service. A hackathon build should not pretend to solve it.

---

## Testing

```bash
.venv/bin/python -m pytest packages/succession/tests   # 259
( cd contracts && forge test )                         # 28, the mirrored Foundry suite
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

Both suites cover the same scenarios and both are green. They are worth keeping
that way in opposite directions: the Foundry suite catches what only a cheatcode
can reach, and the py-evm suite is what runs where Foundry cannot be installed.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/smp-format.md`](docs/smp-format.md) | The package format as a specification another engine could implement |
| [`docs/sibyl-setup.md`](docs/sibyl-setup.md) | Sibyl Pro setup, the memory walkthrough, primitives used |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Everything remaining to be production-ready |
| In-app **Docs** | The same material, alongside the console |

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
