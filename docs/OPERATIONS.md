# Current operation and release boundaries

This describes the release deployed on 9 September 2026. The current contract
and transaction evidence are under `deployments/`; use [AUDIT_STATUS.md](AUDIT_STATUS.md)
for verification and unresolved findings.

## Seller flow

Configure `BASE_SEPOLIA_RPC_URL`, `SUCCESSION_DEPLOYMENT` if overriding the
bundled deployment, and `SUCCESSION_SIGNING_KEY` on the seller machine. Export
these variables in the shell or process manager; the Python CLI does not load
`.env` automatically. Never put a signing key in a shared command or MCP request.

`SUCCESSION_FINALITY_CONFIRMATIONS` sets the receipt depth required before a
chain write is accepted. The default is three blocks on Base Sepolia and one on
local EVMs. Start post-settlement fulfilment and buyer claim only after the
evaluator command returns at that depth. Base derives from Ethereum; its
documented L1-finalized reorg bound is about 13 minutes under normal conditions.
For mainnet assets, pair a longer depth with L1-finalized reconciliation before
retiring external state that cannot be restored.

`succession inventory --db <path> --tenant <tenant>` shows available categories.
`succession list` snapshots the source, applies disclosure and selected scope,
signs and encrypts the package, and fsyncs the private seller vault **before**
broadcasting the listing. The preview describes that selected snapshot.

If interrupted, `succession publish --listing <id>` resumes a prepared vault
entry or republishes an existing listing. It reuses the original encrypted
package and key. It refuses a different signer, deployment, or sale terms.
Back up the vault: a hash commitment cannot reconstruct a lost content key.

Keep `succession fulfil` running. It observes escrow, repeatedly makes the key
available through the authenticated relay, and reconciles confirmed sales into
a local source-tenant seal. Restarting the relay or watcher is recoverable.
Older vault entries without source paths require explicit local retirement.

Scope percentages apply to memory records. Every settled sale transfers the
whole ERC-8004 identity token. A new owner can list that identity again with a
new listing. An old owner cannot list a token they no longer own.

## Buyer flow

`succession buy` approves the payment token and funds escrow. Configure
`SUCCESSION_BUYER_KEY` on the buyer host.
Claim into a **fresh local tenant**, not an existing agent's populated tenant:

```bash
succession claim --listing listing-example --db ~/.sibyl-memory/memory.db --tenant succession-import
```

The request is authenticated as the buyer. The CLI decrypts, verifies the signed
package, imports transactionally, rehashes the destination, and commits an
acquisition journal with the imported records. Repeating the command resumes
that journal without another import or another key request.

Run a dedicated evaluator process with `SUCCESSION_EVALUATOR_KEY` and
`succession evaluate --listing … --db evaluator.db --tenant isolated --yes`.
It alone receives the pre-settlement key, imports into an isolated tenant,
checks the seller signature, re-derives the root, and settles. The buyer runs
`claim` only after settlement; it records the acquisition and certificate
transactionally. If the process stops during buyer import, repeat claim with
the same destination to recover the settlement event and finish completion.
The journal and certificate live in the destination database's
`succession_acquisitions` table. Repeating completion does not duplicate records.
Completion also writes an acquisition entity. A later export of the same
identity automatically carries its ownership history into the signed header,
unless the acquisition is withheld by disclosure policy. This history remains
seller-reported; carrying it forward is not independent verification.

Cancel, refund, and expiry recovery remain contract-authorized operations. The
current web dashboard does not connect wallets or submit transactions. The live
EOA CLI flow is accepted. ERC-1271 request authentication remains covered on a
local EVM, but there is no browser flow for producing that authorization in this
release.

## Service and demo

Run from the repository root:

```bash
pip install -e 'packages/succession[service,chain]'
uvicorn service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Use a persistent `SUCCESSION_WORKDIR`. Ciphertext, metadata, replay nonces and
the listing index persist in SQLite. The key relay holds keys briefly in RAM;
the seller watcher can republish them. A single worker is required while relay
keys and walkthrough sessions are process-local. Horizontal scaling needs
shared ephemeral relay/session storage or appropriate session routing.

The listing index backfills in bounded batches and resumes after restart.
Provide `deployment_block` in a deployment record to avoid scanning predeployment
history. Partial discovery is exposed to clients. Recent blocks are replayed
for shallow reorg recovery; deep reorg recovery needs an operational reindex.
`/api/chain` distinguishes configured-but-unavailable from verified connectivity.

Metadata/key release require a seller signature; key collection requires a
buyer signature. Signatures bind method, path, exact body, chain, contract,
timestamp and nonce. `SUCCESSION_API_TOKEN` protects administrative routes only.
Encrypted envelopes and aggregate market reads are public. Signed headers must
not be cached; key responses use `no-store`.

`/api/walkthrough/*` is an isolated synthetic demo. Every response is marked
simulated. Each visitor has independent state, serialized actions, expiry and a
capacity limit. The deterministic agent uses FTS and record templates, not an
LLM. Explicit messages such as `Tallgrass Brewing target=1000 cost=800` apply
stored margin-floor and opening-premium rules. No real quote is sent.

MCP requires `succession-cli[mcp]` with SDK 2.1.1 or later in the 2.x line.
The `run_command` tool covers the CLI command set. Mutating commands require
`SUCCESSION_MCP_ALLOW_WRITES=1`; keys come from the operator's environment.
Command output and errors are captured in a child process, with no shell or
per-request mutation of the server environment.

## Current release boundary

The deployed model uses mandatory evaluator settlement before buyer key release.
The Base Sepolia contract, Railway service and Vercel frontend were accepted
together, including a hosted restart between key release and evaluation. Local
retirement cannot prevent a file owner copying or modifying SQLite or revoke
remote credentials. Mainnet use still needs an external audit, operational
monitoring, capacity evidence, an operator-approved contract-wallet
authorization tool and deeper L1 finality reconciliation.
