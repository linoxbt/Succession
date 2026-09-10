# Roadmap and release gates

Updated 9 September 2026. [AUDIT_STATUS.md](AUDIT_STATUS.md) records verification;
[OPERATIONS.md](OPERATIONS.md) describes supported behavior.

## Release blockers

- [x] **Delivery/refund policy:** mandatory independent evaluator verification
  and settlement before buyer key release, implemented and verified locally.
- [ ] **Live ACP acceptance:** establish seller/buyer registration and real
  resolved job evidence. Integration code and synthetic fixtures do not prove it.
- [x] **Live evaluator acceptance:** exercise independently derived verification
  and authorized settlement with the selected policy.
- [x] **New coordinated deployment:** deploy the changed contract, service and
  frontend, verify runtime code and configuration, and update deployment records.
- [x] **EOA wallet acceptance:** test funding, signing, claim and settlement through
  supported providers. Contract-wallet authorization passes on a local EVM;
  provider-specific acceptance is still outstanding.
- [x] **Two-host rehearsal:** export/import across the local operator and hosted relay, interrupt
  parties, recover the certificate, and verify seller retirement through existing
  and reopened clients.
- [x] **Independent review pass and finality policy:** Slither/manual review is
  recorded; writes and recovered receipts require three confirmations. This is
  not a third-party professional audit or deep L1 reorg reconciliation.

## Implemented locally

These are source capabilities with regression coverage, not deployment claims.

- [x] Buyer-authenticated key access and seller-authenticated publication/release,
  with exact-body/deployment binding, expiry and durable replay protection.
- [x] Disclosure/consent filtering across storage tiers, signed permissions
  validation, and explicit unverified reputation labels.
- [x] Transactional import/acquisition journal, retryable completion, certificates
  and automatic acquisition history in subsequent same-identity exports.
- [x] Seller vault preparation before broadcast, a consistent listing snapshot,
  publish resumption and repeated key relay until settlement.
- [x] Durable cooperative source-tenant retirement after observed confirmation.
- [x] New-owner identity resale. Partial memory selection still transfers the
  entire identity NFT and retires the source tenant.
- [x] Evaluator-only confirmation, post-settlement buyer claim authorization,
  cancel/refund/expiry controls, exact monetary units and safe shell arguments.
- [x] Per-visitor walkthrough isolation, expiry, capacity limits and serialized actions.
- [x] Remembered margin-floor/opening-premium calculations, citations and input
  validation. The agent is deterministic retrieval, not an LLM.
- [x] MCP coverage of every CLI command through isolated subprocesses, a mutation
  gate and operator-managed signer environment.
- [x] Durable bounded listing discovery, restart cursors, shallow reorg repair,
  and distinct unavailable/incomplete results.
- [x] Deferred console/wallet loading, browser regression CI, generated-reference
  checks, and a clean-container build/smoke check.

## Operational work before a real pilot

- [x] Define evaluator custody for this release: dedicated mode-600 EOA environment,
  distinct from deployer/seller/buyer and funded only with minimal testnet gas.
- [ ] Protect plaintext local memory and seller-vault backups; demonstrate restore
  of memory and its seal/acquisition journals.
- [ ] Add edge rate limits, request timeouts and measured concurrency budgets.
  JSON size limits and bounded demo sessions do not establish sustained capacity.
- [ ] Add structured operational logs, metrics and alerts for missed fulfilment,
  expired escrow, RPC errors and failed local retirement.
- [ ] Extend settlement reorg recovery and listing reindexing beyond the shallow
  replay window, including finality and reconciliation rules.
- [ ] Benchmark large stores and establish a supported ceiling. Export and
  encryption still materialize the package in memory.
- [ ] Use shared relay/session storage before enabling multiple service workers.
  Metadata/ciphertext already persist; keys and demo sessions remain process-local.
  The seller watcher must stay available to republish expired keys.
- [ ] Exercise dispute handling and responsibility for post-settlement failures.
- [ ] Extend browser tests to a complete connected-wallet transaction lifecycle.

## Product and protocol expansion

- [ ] Review disclosure flags and evidence of authority to transfer counterparty
  data; publish applicable product terms and privacy documentation.
- [ ] Seller preview/review UX beyond CLI inventory and data-room commands.
- [ ] Funding/completion/expiry notifications and watchlists.
- [ ] Independent reputation and demand-based pricing backed by verifiable evidence.
  Heuristic valuation and self-reported lineage must retain their labels.
- [ ] A second memory engine, format migrations and independent conformance vectors.
- [ ] Lease, conditional handover, inheritance triggers, merge, split and revocation.
  Percentage filtering alone implements none of their ownership/enforcement rules.
- [ ] Cross-engine lineage, fractional ownership and lending remain exploratory.

## Demonstration work

- [x] Record a fresh demonstration from the changed deployment, including cold
  recall and a deliberate failure/recovery path.
- [ ] Distinguish sample memory, simulated walkthrough settlement, local EVM runs
  and real testnet transactions in every artifact.
- [ ] Confirm current submission requirements and dates before publishing materials.
