**Succession — technical and product review, 7 September 2026**

This is the historical audit. Remediation and verification progress is tracked
in [AUDIT_STATUS.md](AUDIT_STATUS.md); findings below describe the reviewed baseline.

Reviewed the current checkout, including the 33 files already staged when this review began. Existing application changes were preserved. This is an assessment, not a patch set or a formal independent security audit. Security reproductions ran against disposable stores and an in-process EVM; no live purchase, key collection, publication, reset, or settlement was performed.

**Assessment**

Succession is a substantial technical prototype with working memory serialization, cryptographic integrity checks, encryption, import verification, and real Base Sepolia settlement. It is not ready to handle real customer memory or production funds. Its strongest implementation is the portable memory package and the local transfer pipeline. Its weakest areas are the boundaries between seller authorization, buyer access, delivery, settlement, and off-chain recovery.

The distinction matters: all 360 existing Python tests and all 28 Foundry tests passed during this review, yet additional isolated probes reproduced privacy failures, destructive cleanup, fabricated reputation, and authorization replay. Passing the current suite does not establish the broader guarantees made in the interface and documentation.

**What the application is about**

The product treats an agent's accumulated operating context as an asset. Its target asset is the customer book, remembered preferences, operating history, outstanding commitments, and learned rules that make an agent useful over time. It does not transfer model weights, executable agent code, external service accounts, or a general-purpose running AI system.

The seller exports a Sibyl tenant on their own machine. Succession filters and groups records, computes a Merkle commitment, signs a provenance header, encrypts the package, and lists it in a contract. The buyer funds escrow, obtains and imports the package into a local tenant, re-exports the destination to check its root, and submits a confirmation. A matching root makes the contract transfer the payment and the seller's ERC-8004 NFT to the buyer wallet and set an agent seal.

The central useful capability is destination verification: the implementation checks what actually landed in the buyer's store, rather than merely hashing a downloaded file. The central unsolved economic problem is that a buyer who has received plaintext can keep it while obtaining a refund. Identity ownership and possession of memory are different things, and the current system cannot enforce exclusive possession of information.

| Component | Role and current implementation |
|---|---|
| `packages/succession` | Python distribution `succession-cli`, version 0.3.0; CLI, MCP tools, memory adapters, package format, valuation, reputation, delivery and settlement abstractions. |
| `memory/sibyl.py` | Adapter to local Sibyl SQLite stores. Reads the underlying schema directly for enumeration; mostly writes through the SDK, with direct storage operations for some tiers. Only one memory-engine implementation exists. |
| `smp.py`, `canonical.py`, `merkle.py` | Six data directories plus provenance, permissions and integrity manifests. NFC-normalized deterministic JSON; floats deliberately rejected; category-bound, two-level Keccak Merkle tree with distinct leaf/node prefixes. |
| `export.py`, `scope.py`, `redaction.py` | Selection by category or percentage, disclosure filtering, and pruning relationship edges whose endpoints are absent. Percentage selection prefers newer records. |
| `envelope.py`, `provenance.py` | AES-256-GCM encryption and seller signatures over the provenance header. Listing ID and root are authenticated as encryption context. |
| `importer.py`, `transfer.py` | Package verification, fresh-tenant import, destination re-hash, and a richer orchestrated workflow with settlement, local sealing and acquisition records. |
| `contracts/src/ListingContract.sol` | Escrow, NFT transfer, refund/cancellation/expiry and a permanent seal keyed by agent token ID. Uses immutable payment-token, identity-registry and arbiter addresses. |
| `chain.py` | Web3 settlement backend. Checks transaction receipts and decodes settlement outcome from events. Also discovers listings and activity through bounded log scans. |
| `service/app.py`, `registry.py` | FastAPI marketplace and SQLite metadata registry. Reads chain state, accepts seller-authenticated metadata and ciphertext, and relays released keys in process memory. Does not submit live transactions. |
| `web/` | React 18, TypeScript, Vite, Tailwind, Wagmi/Viem and wallet connectors. Landing, overview, marketplace/detail, sell command builder, claims, walkthrough and documentation. Selling and importing remain terminal operations. |
| `agent.py` | Deterministic retrieval and templated responses over Sibyl/FTS5. It demonstrates transferred recall; it is not an LLM agent or autonomous business operator. |
| `acp.py`, `evaluator.py` | ACP job-history integration and optional independent re-derivation/arbiter settlement. These are library capabilities, not a mandatory independent verification service in the normal marketplace flow. |

**What is real, synthetic, simulated, or unfinished**

Read-only checks of the [hosted overview API](https://successmarket.netlify.app/api/overview) returned six chain listings: four confirmed, one refunded and one open. Settled volume was 4,000,000 minor units, displayed as 4.00 testnet USDC; open volume was 1.00 testnet USDC. All six listings belong to one seller. Five have metadata; none of the six had a published envelope at the time of review. The open listing, `listing-670`, has neither metadata nor an envelope.

A direct Base Sepolia RPC check returned chain ID 84532 and 6,514 bytes of deployed code at `0xBE16BD086BF00c90B2E1e49E5393b3C18519927E`. Recompiling the current source with the repository's solc settings produced matching runtime bytecode after masking immutable slots. This validates the connection between reviewed source and deployed code; it does not prove every off-chain assertion associated with a sale.

| Surface | Classification |
|---|---|
| Cryptography and Sibyl export/import | Real implementation, exercised by tests and isolated stores. |
| Hosted chain listings and settlement | Real testnet contract activity. This is not mainnet volume or evidence of independent market demand. |
| Five transfer demonstrations | Real testnet settlement attempts using seeded, invented operating memory. Four successful transfers and one deliberate mismatch/refund. |
| Three rich marketplace demonstration rows | Hardcoded display fixtures in `service/demo.py`. Invented prices, counts, roots, job figures and reputation. Explicit `demo: true`, separate API collection, excluded from actual totals. |
| Walkthrough | Synthetic memory, real local export/encrypt/import/re-hash, simulated `LocalSettlement`. No live payment or NFT transfer. |
| Agent chat/recall | Actual retrieval from the selected tenant, followed by deterministic text composition. No LLM inference. |
| `MockService` | Build-time fixture mode selected by `VITE_SERVICE=mock`. The selector is not restricted to development builds despite its comment claiming development-only behavior. |
| Valuation | Computed heuristic reference, not discovered market value. Uses a configurable base and clamped factors; journal outcome detection relies on words such as “accepted” or “cancelled.” |
| Reputation | Computed from supplied provenance and memory, without independent historical validation. See finding 8. |
| Virtuals ACP | Reader, snapshot, sync and handover code exists. No ACP credentials were populated in this checkout's `.env`, and no hosted real listing exposed ACP history. This does not prove that no registration exists anywhere outside the project. |
| Evaluator | Real local code and tests; not required before key release and not enforced as the exclusive settlement authority. |
| Lease, conditional transfer, inheritance triggers, merge, split/revoke workflows | Roadmap or design ideas rather than complete user-facing implementations. Category selection exists; it is not a complete economic splitting/resale model. |
| Recorded artifacts and catalog helpers | Older demo/recording infrastructure remains in scripts and the package. The current marketplace HTTP client does not silently fall back to a recording. |

**Reproduced defects and high-priority gaps**

The severity labels below describe practical impact in this application. They are not CVSS ratings.

**1. Critical: an unauthenticated caller can collect a purchased memory's decryption key.**

[`service/app.py:471`](/root/succession/service/app.py:471) checks only that the listing is escrowed and a key is present. It does not authenticate the request or compare a caller to the on-chain buyer. The ciphertext route is intentionally public. The isolated probe released a key as the seller, then fetched the correct key with no authentication and received HTTP 200. The key response also lacks an explicit `Cache-Control: no-store` policy.

Authenticate the buyer with a short-lived challenge tied to chain, contract and listing, and support the wallet types the UI offers. Consider wrapping the content key to a buyer-controlled encryption key instead of relaying a raw bearer secret. Never cache key responses. Merely checking that somebody paid is not an access-control decision about who may read.

**2. Critical: failed transfer cleanup can delete existing buyer memory.**

[`transfer.py:183`](/root/succession/packages/succession/src/succession/transfer.py:183) catches every import exception and calls `buyer_sink.purge()`. [`importer.py:165`](/root/succession/packages/succession/src/succession/importer.py:165) raises when the destination already contains records. The orchestrator consequently purges the very pre-existing data that the importer refused to overwrite. The isolated probe put a personal record in the destination, attempted a transfer, received a refund outcome, and found the destination empty.

Validate destination ownership and emptiness before beginning the operation. Import into an operation-owned staging tenant or transactional snapshot. Cleanup must remove only data created by that operation. The direct `claim` path does not use this purge handler; this finding applies to the richer orchestrator and its callers.

**3. Critical: journal disclosure flags are ignored by export.**

[`redaction.py:211`](/root/succession/packages/succession/src/succession/redaction.py:211) reads every record's disclosure from `record.get("body")`. Journal records store their metadata in `extra`, not `body`. The valuation code itself looks for journal flags in `extra`, making the mismatch explicit. A journal event marked `transferable=False` in `extra` still exported its private acted content in the isolated probe.

Define one disclosure accessor per record kind and use it throughout export, inventory, valuation, preview and import. Audit relation/reference metadata as well. Tests need coverage across every storage tier, not just marked entity bodies.

**4. High: permissions can change without invalidating package verification.**

[`provenance.py:109`](/root/succession/packages/succession/src/succession/provenance.py:109) creates a signed `permissions_hash`, but [`importer.py:83`](/root/succession/packages/succession/src/succession/importer.py:83) never recomputes that hash against `package.permissions`. Replacing the entire permissions document left `verify_package` successful with the original seller signature and commitment.

Recompute and compare the permissions hash before any write. Also validate package version, category declarations and manifest consistency. AES-GCM protects an intact envelope in transit, but it does not repair a standalone package verifier that accepts changed disclosure documents.

**5. High: seller authorization is a reusable credential, not a signature over the requested mutation.**

[`publish.py:239`](/root/succession/packages/succession/src/succession/publish.py:239) signs only a fixed domain string and listing ID. The same header authorizes metadata publication and key release indefinitely. No request-body digest, action/path, chain, contract, expiry or nonce is authenticated. Using the exact original header with a different metadata body changed the listing name with HTTP 200; reusing it on the key route overwrote the released key with a different 32-byte value.

An attacker needs access to a valid header for this attack; this is distinct from the anonymous read in finding 1. Bind authorization to the complete operation and reject replay. Persist the verified signed metadata so readers can verify the seller's actual claims rather than trusting the service's stored copy.

**6. High: the normal CLI sale does not finish the local succession lifecycle.**

[`cli.py:634`](/root/succession/packages/succession/src/succession/cli.py:634) imports and prints a root. [`cli.py:570`](/root/succession/packages/succession/src/succession/cli.py:570) settles on chain and prints that the seller copy is sealed. Neither runs the off-chain seal or acquisition-record/certificate work in `execute_transfer`. The seller vault does not store the source database path and tenant needed by a later reconciler, and `fulfil` only watches for key release.

There is a second, separate limitation: [`open_tenant`](/root/succession/packages/succession/src/succession/memory/sibyl.py:429) returns an unguarded adapter. Reopening a database after adding its tenant to `SealRegistry` still allowed a write in the probe. The guard is an opt-in wrapper, and `credential_revoked` is a local ledger field rather than actual revocation of the user's Sibyl credentials.

Implement a durable transfer record shared by CLI/MCP flows, record source/destination references, and reconcile finalized chain events into the supported local runtime. Be precise that a cooperative runtime can enforce its own seal; an owner-controlled SQLite file and arbitrary external code cannot be remotely made unwritable by this wrapper. The default export also does not automatically load the previous acquisition's lineage; existing resale tests supply that chain explicitly.

**7. High: browser confirmation has an impossible prerequisite.**

[`ListingView.tsx:339`](/root/succession/web/src/dash/ListingView.tsx:339) renders confirmation only when the listing is escrowed and `listing.delivered_hash` is nonempty. The contract sets that field inside `confirmTransfer`, which also transitions the listing to confirmed or refunded. Thus the normal contract state never satisfies the UI condition. The claims screen gives prose instructions but no equivalent usable confirmation action.

Let a buyer paste or import the root produced by their local claim, validate it, and submit it while escrowed. Show the on-chain commitment alongside it. Do not default to the publicly known commitment and claim that constitutes destination verification. Provide actionable refund, cancel and expired-escrow recovery controls too; naming contract functions in prose is not a recovery workflow.

**8. High: reputation and historical verification claims are forgeable.**

[`reputation.py:141`](/root/succession/packages/succession/src/succession/reputation.py:141) considers a lineage link well formed based on shape, including a `0x` prefix and length; it does not verify a past transaction or a prior owner's signature. A seller-signed package containing five invented owners, invented dates, non-hex “hashes” of the expected length, and an asserted memory version passed package verification and scored **92.00 / established**.

The service also stores and returns seller-supplied preview/reputation JSON; it does not recompute the score on each marketplace read, despite the advertised model saying it does. ACP records copied into memory likewise require independent verification before being treated as externally validated earnings.

Persist evidence for each lineage edge, verify the evidence against the relevant chain and owner, and distinguish asserted, signature-checked, chain-checked and destination-verified data. Until then, label the score a heuristic over seller-supplied history. A valid current-owner signature proves who made a claim, not that the historical claim is true.

**9. High design limitation: funding escrow does not guarantee payment for disclosed memory, even with an arbiter configured.**

[`ListingContract.sol:280`](/root/succession/contracts/src/ListingContract.sol:280) permits the buyer or arbiter to confirm. A mismatching buyer root refunds. The buyer can also call `refund` directly while escrowed. Appointing an evaluator adds another allowed caller; it does not remove the buyer's ability to receive plaintext and refund before the evaluator settles. The README acknowledges part of this risk, but language suggesting the evaluator closes it is too strong.

Choose and document the commercial trust model. A pilot could use agreed counterparties and a mandatory delivery/dispute policy. A production design needs explicit rules governing key release, acknowledgment, evaluation and refund rights. Merely invoking the current evaluator more often does not solve the protocol problem.

**10. High: a fresh Docker build lacks a required build hook.**

[`Dockerfile:36`](/root/succession/Dockerfile:36) copies the Python manifest, README and source tree before installing the package, but omits `packages/succession/hatch_build.py`. The manifest now declares that hook. Building a temporary copy with exactly that file set failed with `OSError: Build script does not exist: hatch_build.py`.

Copy the hook before installation and add a clean container build to CI. The running hosted service proves an earlier image started; it does not prove today's Dockerfile can build the current checkout. The reproduction checked the package build prerequisite, not a full Docker-engine build.

**11. High correctness gap: partial-sale previews describe unsold memory.**

[`transfer.py:126`](/root/succession/packages/succession/src/succession/transfer.py:126) passes the full seller to valuation and `build_preview` without the selected scope. A preferences-only sale exported **4 records**, while its preview advertised **49 total records** and **12 sellable relationships**. Inventory-driven scope filters consequently describe what exists in the source, not necessarily what this particular listing sells.

Build the advertised asset statistics and reference valuation from the exact immutable selected export. If full-store inventory is useful, expose it separately with explicit labels. Preview, package, signing and listing should share one snapshot.

**12. Medium privacy/correctness gap: preview and valuation use inconsistent consent gates.**

`build_preview` filters some entity totals using `transferable`, while inventory uses `may_transfer` including consent. A public relationship with `consent=withheld` was reported as unsellable in inventory but still appeared in public counterparties and the total record count. This was not a private-body leak in the tested case; it demonstrates inconsistent handling of a withheld record. Valuation also uses `transferable` rather than the combined consent check.

Make the same resolved disclosure policy authoritative for all sale-related outputs. Also distinguish a seller-entered consent basis from independently documented consent; unmarked records currently default to contractual and transferable.

**13. High reliability gap: relay restart can strand delivery after successful key release.**

[`service/app.py:130`](/root/succession/service/app.py:130) holds keys only in `STORE.released`. [`fulfil.py:139`](/root/succession/packages/succession/src/succession/fulfil.py:139) marks a listing done after the relay accepts its key and stops sending it for that watcher lifetime. If the relay restarts before collection, the key disappears while the seller process believes delivery is done. Multiple workers also have different key maps. Released keys are not automatically expired or removed on settlement.

Use an acknowledged delivery state and durable protected storage, or re-release idempotently until the correct buyer has acknowledged retrieval or settlement completes. Recovery needs to survive both seller and relay restarts. The seller vault is already durable, contrary to some older roadmap descriptions; the relay stage is the remaining volatile link.

**14. High reliability gap: chain commitment precedes durable vault preparation.**

`list_asset` posts the listing before encrypting the package, and `publish_listing` writes the vault afterward. A crash or filesystem failure after the listing transaction can leave a valid on-chain listing without its durable deliverable. `publish_listing` also exports once to derive an ID and again inside `list_asset`, then re-reads for valuation/preview. A concurrently changing source can make these representations disagree.

Prepare and atomically persist a single snapshot, encrypted package and recovery metadata before broadcasting. Track prepared, submitted, mined, published, escrowed, delivered and settled states explicitly. Reorg and confirmation-depth handling remains separate work.

**15. Product constraint: the transferred identity can never be sold again through this contract.**

[`ListingContract.sol:186`](/root/succession/contracts/src/ListingContract.sol:186) rejects any listing for a sealed agent ID. Settlement permanently seals that ID, including for the new owner. An isolated resale by the new owner reverted with `AgentAlreadySealed()`. Partial sales also move the entire NFT and use the same seal semantics.

This may be an intentional one-time retirement model, but it conflicts with ordinary resale, multi-owner lineage and repeated partial-sale expectations. Decide whether the asset is an identity, a memory edition, a scoped license, or a retirement handover to a different successor identity. Model those separately if they need different lifecycle rules.

**16. Medium: chain discovery is incomplete and failures can look like empty markets.**

`listed_ids` and `activity` scan only the last 120,000 blocks and suppress errors for individual windows. Registry holdings scan only 60,000 blocks. The metadata union helps preserve known listings but does not discover old unregistered rows indefinitely. Activity uses inclusive window endpoints without deduplicating boundary events. `chain_status` reports chain mode from the deployment file alone, and overview can report `chain: true` even if marketplace fell back to a disconnected result. `ChainSettlement.get` maps broad RPC exceptions to “no such listing.”

Index from the deployment block with durable cursors, deduplicate by transaction/log index, handle reorgs, and expose data freshness and completeness. Treat unavailable, incomplete and genuinely empty as different states. Preserve escrow deadlines and event timestamps in the API instead of discarding them.

**17. Medium: the public shared walkthrough has no session isolation or write gate.**

[`service/walkthrough.py`](/root/succession/service/walkthrough.py) exposes reset, buy, transfer, messaging and write-attempt endpoints without `require_admin`. Every visitor shares one `_State` and one set of files. Reset deletes that shared walkthrough directory. Two viewers can invalidate one another's sale, and repeated requests impose work on the same service as the marketplace. The shared API token does not protect these routes despite older documentation claiming every mutation is gated.

Give demonstrations per-session state and bounded resource use, or deploy them separately. The synthetic-data separation from the real registry is good and should remain.

**18. Medium: several UI labels overstate the evidence or use the wrong unit.**

- `VerificationBadge` calls equality between a supplied manifest root and the chain root “merkle verified”; the marketplace verified filter only checks that a manifest root exists. Neither establishes successful import or the authenticity of the entire published manifest.
- Delivery steps are marked completed from settled state or a submitted hash, even though the contract cannot observe actual delivery/import.
- The overview says “5 of 6 sellers published a data room” using listing counts. There is only one seller in the observed market.
- Generated provenance, permissions and integrity-proof directories are labelled “coming soon,” even though they already ship in packages. They are generated metadata, not future features.
- Claims treats failed/empty holdings discovery as “this wallet holds no ERC-8004 agents.” A failed or incomplete scan is not proof of zero holdings.
- The picked successor is transformed into a tenant-name string; it is not a binding that makes the contract transfer memory into that specific agent. The contract transfers the seller's NFT to the buyer wallet.
- The open hosted row remains fundable in the UI despite having no published ciphertext. Buyers should see and acknowledge unavailable delivery material before funding.

Use narrow labels such as “commitment matches,” “seller signature verified,” and “destination verified.” Preserve uncertainty and differentiate ownership of an NFT, possession of a package, and a completed local import.

**Other implementation and maintenance observations**

The canonical format's rejection of floats is defensible but limits compatibility with ordinary JSON memories containing scores, probabilities or fractional measurements. Add a preflight compatibility report rather than discovering this after a user starts listing. Direct reads of Sibyl's schema also require a supported-version policy and migration tests; the dependency currently has a broad lower bound.

Import is a series of writes, not one staged transaction. The direct claim path does not compensate for every partial failure, and envelope opening is outside the richer orchestrator's import/refund handler. A decrypt error or a settlement exception can therefore leave a different intermediate state than the blanket “every failure refunds and leaves nothing behind” story suggests. Retry and recovery need to be designed for each transition.

The MCP surface exposes useful tools and has a write opt-in, but some mutation tools accept a private key as an argument, assign process-wide environment variables, and delegate to a printing CLI while returning only an exit code. Prefer a shared structured application layer and operator-managed signer references. This avoids keys in model/tool transcripts, cross-call environment state, and weak results for programmatic callers. These concerns were identified by code inspection; protocol-transport corruption was not claimed or reproduced here.

The Python suite has good coverage of deterministic hashing, tampering, import fidelity and individual contract rules. Its coverage is weaker for adverse lifecycle combinations and actual browser/CLI completion. Some tests encode the flawed assumptions: for example, the funded-key test retrieves a key without buyer authentication and treats that as success. The resale test exports with a different successor identity and an explicitly supplied provenance chain; it does not prove resale of the transferred NFT through the live workflow.

The read-only runtime dependency audit (`npm audit --omit=dev`) reported two vulnerable dependency nodes: one high-severity `axios` node and one moderate-severity `@coinbase/cdp-sdk` node, both transitive and both with fixes reported available. Axios advisories include [request-construction prototype-pollution gadgets](https://github.com/advisories/GHSA-mmx7-hfxf-jppx) and [form serialization recursion](https://github.com/advisories/GHSA-pmv8-rq9r-6j72). These are dependency findings, not demonstrated exploits against Succession; some affected adapters are Node-specific. Update the relevant wallet dependency chain and retest wallet connection and signing. No dependency upgrades were applied during this review.

README, HANDOFF, ROADMAP, service README and `.env.example` contain conflicting generations of the product. Examples include deployed versus undeployed contracts, completed versus pending testnet transfers, six seeded marketplace rows versus chain rows plus three demo rows, old `/api/demo/reset` instructions, recorded-mode fallback claims, shared-token descriptions, and claims that no memory reputation exists. The generated command reference is current; that automation is a useful pattern for deployment status and endpoint documentation too.

**Product and interface recommendations**

Keep the main proposition concrete: “Transfer an agent's operating memory and verify what the successor received.” The broader “property layer” thesis is understandable once the user has seen a specific handover. A freight agent continuing a customer's open quote is a clear demonstration; present the synthetic source data and the real execution evidence together.

The current visual system is restrained and coherent: white/navy surfaces, consistent typography, readable panels, and explicit demonstration labels. Eight primary routes rendered without uncaught JavaScript errors in a local Chromium smoke check using captured read-only API responses. At 390px, reduced-motion rendering fit the viewport. The first normal-motion capture showed transient horizontal overflow; it was not established as a persistent layout defect. Large blank regions in full-page captures can also result from below-fold reveal elements not being scrolled into view, so those screenshots should not be mistaken for missing app data.

The console devotes a large amount of space to explaining the protocol. Keep that depth in Docs and data-room details, while making the transaction pages task-oriented: what is for sale, what is verified, what remains uncertain, what action is available now, and how to recover. The initial wallet bundle is approximately 871 KB minified / 214 KB gzip; defer wallet-heavy code from the marketing page where practical. The production build succeeded with chunk-size and third-party annotation warnings, not compilation failures.

Prioritize a single complete acquisition over adding more marketplace breadth. An unconnected visitor should understand the asset without setting up tools. A serious buyer should get one ordered setup/claim/verify/confirm path with persisted progress. A seller should receive a compatibility check, disclosure inventory, exact scoped preview and recovery record before paying gas. Do not require a pre-existing successor NFT where the actual import only requires a fresh local tenant unless the identity model is deliberately changed to enforce that requirement.

**Recommended order of work**

1. Protect memory and existing stores: buyer-authenticated key access, no-store responses, operation-bound seller signatures, correct per-tier disclosure handling, permissions-hash validation and nondestructive import rollback.
2. Finish one normal sale: root handoff to the web confirmation action, source/destination transfer records, post-settlement sealing within the supported runtime, acquisition provenance and certificates, and usable refund/cancel/expiry recovery.
3. Fix reliability: durable acknowledged key delivery, prepare-before-broadcast, snapshot-consistent previews, event reconciliation, and the Docker hook copy. Add a fresh-container CI job.
4. Correct the evidence model: externally verified lineage/ACP history or explicit self-reported labels; separate identity, memory edition and scoped transfer semantics; decide the buyer/evaluator refund policy.
5. Add meaningful end-to-end tests: real CLI subprocesses and separate stores, browser funding through confirmation, restarts at each lifecycle boundary, wrong buyers, replayed requests, pre-existing destination records, and consent in every tier. Keep destructive probes confined to temporary fixtures.
6. Refresh the demo and documentation only after those behaviors are verified. Publish a concise generated status manifest distinguishing live chain evidence, sample memory, simulated settlement and unavailable integrations.

For a near-term demonstration, focus on making these boundaries honest and the one supported path complete. For a real pilot, add account/signing policy, rate limits, observability, backup/recovery and externally reviewed settlement code before onboarding real counterparties. Privacy and rights to transfer customer data also require an operator-defined policy and evidence; flags alone do not establish those rights.

**Validation record and limits**

- Python: `pytest packages/succession/tests -q --disable-warnings -o faulthandler_timeout=60`, completed successfully outside the sandbox. Independent collection confirmed 360 tests. The initial sandbox run hung in FastAPI/AnyIO; a minimal unrelated TestClient reproduced that environment issue, and those stalled review processes were stopped.
- Solidity: `forge test -vv`, 28 passed, including a 256-run fuzz case.
- Frontend: `npm run build`, successful. The generated command reference, README command block, packaged contract ABI and packaged deployment record were current.
- Browser: eight primary routes with captured live read responses and no live mutations; no uncaught page errors. Wallet signing, real browser purchase and two-machine handover were not performed.
- Live evidence: hosted overview response and direct read-only Base Sepolia RPC; compiled runtime matched the deployed code after masking immutable fields. This was not a full independent reconstruction of every historical off-chain transfer.
- Adverse probes: anonymous key read, seller-signature replay across changed payloads/actions, existing-destination purge, altered permissions acceptance, nontransferable journal export, inconsistent consent preview, full-store preview of a partial package, fabricated signed lineage and blocked NFT resale. These reproduced against temporary stores/local EVM.
- Container prerequisite: package build with the exact Python files copied by the Dockerfile failed on the missing custom build hook. No production deployment was changed.
- Runtime dependency audit: two transitive vulnerable nodes, one high and one moderate; fixes reported available. Development dependencies and Python dependency advisories were not included in this scan.

Temporary review artifacts are under `/tmp/succession-review-*`; the reproduction script is `/tmp/succession_review_probes.py`. This document preserves the conclusions independently of those temporary files. No implementation fixes, deployments, commits, pushes, or live transactions were made as part of the review.
