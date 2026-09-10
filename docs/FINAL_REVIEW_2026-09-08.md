# Remediation review — 8 September 2026

> Historical predeployment review. The coordinated release and later acceptance
> evidence are recorded in [RELEASE_ACCEPTANCE_2026-09-09.md](RELEASE_ACCEPTANCE_2026-09-09.md).

**Production-ready: no.** The local fixes materially improve the audited paths,
and the delivery/refund policy is now implemented, but live release acceptance remains unresolved.
This review does not declare the historical audit clean or certify the system.

## Changes completed in the resumed pass

| Finding | Fix and evidence |
|---|---|
| Acquisition history disappeared on resale | `export.py` carries the completed acquisition entity into the next same-identity signed header. A regression verifies the new signature and history, excludes unrelated identities, and respects withheld disclosure. Historical claims remain seller-reported. |
| Pricing message validation | `agent.py` consumes complete target/cost values and rejects missing, duplicate, malformed, negative, nonfinite and overflowing values. Tests also verify the transferred memory preserves the opening-premium and margin-floor behavior. |
| Broken live ACP imports | `acp.py` now imports `VirtualsACP`, the Sepolia configuration and `ACPContractClient` from their actual SDK modules. The new SDK regression exercises the real API client and constructor signature without external calls. Previously, the adapter could fail before reaching registration. |
| ACP dependency incompatibility | The local environment now resolves all declared extras together. ACP-compatible Ethereum libraries are installed and `pip check` passes. CI installs ACP alongside MCP, checks requirements and imports the actual SDK classes. |
| MCP completion and documentation | Tests verify CLI-command schema parity, the mutation gate, isolated failures, absence of private-key request fields, and remembered quote calculations through the MCP tool. |
| Contradictory operating instructions | README and generated guide now include the local destination in confirmation guidance and describe refund recovery accurately. Handoff/roadmap no longer claim the project is finished or only blocked by connectivity. |

The prior remediation also implements buyer authentication, replay protection,
tier-aware disclosure, permissions validation, transactional import/recovery,
seller retirement, durable listing preparation, repeated key relay, identity
resale, isolated walkthroughs, bounded discovery and browser recovery controls.
Per-finding evidence remains in [AUDIT_STATUS.md](AUDIT_STATUS.md).

## Verification

- Python: 429/429 tests pass against the ACP-compatible dependency set. Two
  upstream deprecation warnings remain in WebSockets and Starlette test support.
- Solidity: 30/30 Foundry tests pass, including the 256-run fuzz test and
  new-owner resale.
- Browser: 13/13 Playwright regressions pass.
- Frontend: production TypeScript/Vite build passes. The wallet chunk remains
  large at about 872 KB minified / 214 KB gzip.
- Packaging: final clean Docker build passes; the network-disabled container
  imports the FastAPI service, loads the packaged contract ABI and passes
  `pip check`.
- Generated assets: the CLI/reference documentation, frontend ABI and packaged
  contract/deployment data match their sources. `git diff --check` passes.

Tests use temporary stores, local EVMs and controlled API responses. No test
transaction is represented as a live purchase. A green build does not validate
deployment state, provider-specific wallet behavior or real ACP jobs.

## Remaining findings and release gates

| Severity / status | Location | Impact and required next step |
|---|---|---|
| **Resolved locally, S7** | `contracts/src/ListingContract.sol`, `service/app.py`, `fulfil.py`, `evaluator.py` | The configured evaluator alone receives the pre-settlement key and calls `confirmTransfer`; the buyer key route opens only after confirmation. Local EVM and HTTP tests cover authorization, verification, settlement, refund, replay protection and recovery. Deployment is pending. |
| **Release acceptance unverified, M4** | `acp.py`, `evaluator.py`, deployment configuration | Corrected SDK wiring and local tests do not prove external registration, real job history or live evaluator acceptance. Record real evidence before claiming these integrations are operational. |
| **Deployment pending** | `deployments/`, service and web release | Bundled testnet records predate the contract/security changes. Deploy and verify all changed components together before relying on their new guarantees. |
| **Wallet / recovery acceptance pending** | `web/src/chain/`, CLI claim/evaluate, seller watcher | Contract-wallet authorization passes on a local EVM. Exercise supported providers and separate hosts, including evaluator operation, restart after settlement and seller seal recovery. |
| **Medium — operational finality / capacity** | `chain.py`, `service/chain_index.py`, service runtime | Mined settlement receipts are treated as final; shallow index repair is not settlement reorg handling. Define finality/reconciliation, backups, monitoring and measured traffic/size limits. |

Local sealing is cooperative enforcement through Succession-opened clients. It
does not revoke external credentials or prevent an owner from copying/editing
their own files. Ownership-history preservation is not independent historical
verification. These limits must remain visible in product claims.

No deployment, live transaction, commit or push was performed during remediation.

## Implementation score

- Requirements coverage: **95/100** — the audited local workflow includes
  mandatory evaluator settlement, recovery and resale. External acceptance and
  several broader roadmap primitives remain open.
- Code quality: **90/100** — strong deterministic and adversarial regression
  coverage, explicit state recovery and improved dependency checks. Remaining
  concerns include large in-memory packages, process-local relay state and
  settlement finality handling.
- Production readiness: **65/100** — the high-severity economic flaw is closed
  in source, but undeployed security changes, no independent contract review,
  evaluator key custody, and missing live/two-host acceptance preclude a
  production claim.
