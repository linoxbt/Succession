# Audit remediation status

This tracks the findings in the September 2026 conversation audit. The remediated
contract, API and frontend were deployed together on 9 September, followed by
live evaluator, buyer-wallet and restart-recovery acceptance.

| Findings | Status | Evidence / remaining work |
|---|---|---|
| B1 destructive cleanup; S2 tier disclosure; S3 permissions; S10 consent | Verified locally | 21 adversarial cases pass; roundtrip/transfer/scope/valuation compatibility checks pass; credentials constructor spy updated and verified |
| S1 buyer key authentication; S4 request replay | Deployed and accepted | API + adversarial tests plus authenticated live seller/evaluator/buyer requests through Railway; raw-body/deployment-bound signatures, expiry, durable nonce consumption, no-store responses |
| B3 scoped preview; B5 durable preparation; P3 snapshots | Verified locally | 68 export/roundtrip/transfer/data-room/publisher/regression tests pass; disk failure before broadcast and mutation during broadcast covered |
| B4 relay recovery; B7 transfer recovery; M1 lifecycle; S6 sealing | Deployed and live-recovered | Railway was restarted after escrow/key release; evaluator received 404, seller republished from a separate vault, evaluator settled, and buyer resumed its durable journal. External credentials are not claimed revoked. |
| M3 asset lifecycle; B12 relisting | Deployed and accepted | A refunded live identity was relisted under a new id and evaluator-settled; the CLI guide distinguishes memory scope from whole-token transfer. |
| S7 delivery/refund policy | Deployed and accepted | Dedicated evaluator `0x518477…f31b` alone receives the pre-settlement key and calls `confirmTransfer`; four matching deliveries released and one deliberate mismatch refunded in the five-sale ledger. |
| S5 reputation; S9 metadata schemas | Deployed | API tests pass; nested schemas, chain identity/domain checks, malformed legacy preview isolation, explicit unverified reputation |
| S11 walkthrough isolation | Verified locally | Independent random visitor sessions, per-session serialized operations, expiry and capacity limit; two-visitor reset-isolation regression passes. |
| B2 confirmation; M2 recovery; B8–B11, B13–B16 UI | Live EOA wallet flow accepted | Buyer approved USDC, funded escrow, authenticated after settlement, imported 49 records and recovered its certificate. The web surface is now read-only; transactions use role-specific CLI environments. |
| M4 live ACP/evaluator | Evaluator accepted; ACP jobs open | Real ERC-8004 agents were registered and transferred. The dedicated evaluator signed and submitted live verdicts. External Virtuals ACP registration/job acceptance was not exercised. |
| M5 agent behavior | Verified locally | Remembered margin floor and opening premium produce exact decimal quotes and citations, survive memory transfer, and reject malformed/nonfinite/negative/overflowing or duplicate message inputs. Deterministic retrieval; no LLM or real counterparty quote submission. |
| M6 MCP; S12 signer secrets | Verified locally | Parser-to-tool schema parity covers all CLI commands. Mutation gate, isolated output/errors, operator-managed keys, and read-only pricing tool verified. No private-key request fields or request-driven environment mutation. MCP SDK >=2.1.1,<3. |
| B6 container; M7 release checks | Deployed | Docker service is live on Railway with a persistent `/data` volume; Vite frontend is live on Vercel and proxies the same API. |
| S13 dependencies | Compatibility fixed locally; no independent Python advisory audit | Prior web npm audit reported zero vulnerabilities, including development dependencies. ACP's Ethereum dependency conflicts were repaired by resolving all extras together; `pip check` passes. CI now installs ACP alongside MCP and checks SDK imports and dependency consistency. |
| S8 zero listing ID | Deployed | Foundry regression passes and the checked deployment input exactly matches reviewed bytecode. |
| P1 indexing; P2 health | Deployed with policy | Durable index starts at deployment block. Writes and recovered receipts require three confirmations. Deep Base/L1 reorg reconciliation remains operational work for mainnet. |
| P4 frontend loading | Verified locally | Browser wallet and listing components were removed. The frontend now mirrors Triacta's component structure, theme, local Space fonts, motion, dashboard sidebar and guide layouts. |
| M8 documentation | Reconciled | README, generated guide, operations, handoff, roadmap and service/web docs distinguish live release evidence, synthetic demos and remaining external gates. |

Pilot readiness on Base Sepolia is established for the tested EOA flow. This is
not a mainnet or external-audit certification; live Virtuals ACP jobs,
monitoring, capacity and deeper reorg reconciliation remain.

## Resumed review, 8 September 2026

The resumed pass fixed automatic resale lineage, quote-message validation, real
ACP SDK imports and environment dependency incompatibility. The SDK regression
does not contact ACP or prove registration. Existing user changes are preserved.

The final compatible-dependency suite passed all 429 tests; the Foundry suite
passed 30 tests, the browser suite passed 13 tests, and the production web and
clean container builds passed. Full evidence and limits are recorded in
[FINAL_REVIEW_2026-09-08.md](FINAL_REVIEW_2026-09-08.md).

On 9 September the user selected mandatory evaluator verification and settlement
before buyer key release. A coordinated contract/service/web deployment,
five-sale ledger and separate-host recovery acceptance then completed. See
[RELEASE_ACCEPTANCE_2026-09-09.md](RELEASE_ACCEPTANCE_2026-09-09.md).
