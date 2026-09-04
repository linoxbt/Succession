# Roadmap — what's left to be production-ready

An honest inventory. Written against what is actually in the repository today,
not against an idealised version of it.

**Legend** — `P0` blocks the hackathon submission · `P1` blocks a real pilot ·
`P2` blocks general availability · `P3` is the protocol thesis

---

## P0 — Blocks submission (deadline 10 September)

These need credentials and a network route, not code. The code paths are
complete and tested; `./scripts/finish_integrations.sh` runs them with
preflight checks.

- [ ] **Register both demo agents on the Virtuals ACP Service Registry.**
      Through the ACP Tech Playbook — it issues the whitelisted wallet and
      entity id. An unregistered agent cannot be discovered or hired, so this is
      a prerequisite, not a detail. Do it first; it gates everything else.
- [ ] **Sync real ACP job history** — `succession-acp sync`. Until this runs the
      data room shows self-reported figures only, which is exactly the weakness
      the integration exists to remove.
- [ ] **Fund a Base Sepolia deployer key** (faucet: docs.base.org/get-started/get-funds).
- [ ] **Deploy `ListingContract`** — `python scripts/deploy_base_sepolia.py`.
- [ ] **Run 5 real transfers** — `python scripts/run_transfers.py --count 5`.
      Each gets its own agent identity and tenant; one is corrupted on purpose,
      because five successes say nothing about the refund path.
- [x] **Point `IDENTITY_REGISTRY_ADDRESS` at a real ERC-8004 registry.** Done:
      `0x7177a6867296406881E20d6647232314736Dd09A` on Base Sepolia, verified on
      chain (ERC-721 by `supportsInterface`, live agents, every function
      `ListingContract` calls present). It is the default; the ERC-721 stand-in
      is now reachable only from `--local`, and the deploy script exits rather
      than build on an address holding no code.
- [ ] **Re-record the hosted artifact** — `python scripts/record_run.py` folds
      the real ledger in, so the console's Transfers view shows actual
      transactions.
- [ ] **The two-machine rehearsal.** Seller and buyer on genuinely separate
      hosts, twice, before recording. Not simulate-able with two browser tabs.
- [ ] **Film the 2–5 minute demo.** Must include the fresh-session recall beat.
      The beats are built and `python -m succession.demo` prints them in order.
- [ ] **Deploy the site.** Netlify project `succession-memory` exists and
      `netlify.toml` is complete; link the repo under Build & deploy.
- [ ] **Two build-in-public posts** on X or Farcaster.
- [ ] **Verify the contract on Basescan** so a judge can read the source at the
      address.

## P1 — Blocks a real pilot

### Security

- [ ] **Third-party contract audit.** `ListingContract` has 27 py-evm tests, 28
      Foundry tests and a fuzz case, which is not an audit. Custody code that has
      not been audited should not hold anyone's money.
- [ ] **Key management.** Signing keys are read from the environment. Production
      needs a KMS or HSM, per-agent key isolation, and rotation without
      invalidating historical provenance signatures.
- [ ] **Replace `LocalSettlement` in every production path.** It exists for
      tests and offline development; a config that silently falls back to it
      would report settled sales that never touched a chain. Make the fallback
      impossible rather than discouraged.
- [x] **Authenticate the service.** Done, narrowly: every mutating route is
      behind `require_write_access`. With `SUCCESSION_API_TOKEN` set it requires
      a bearer token; unset, it serves writes to localhost only and refuses them
      from anywhere else, so a deployed service cannot be written to by default.
      Reads stay open by design.
- [ ] **Rate-limit the service.** Still absent. The auth gate bounds *who* can
      write, not how often, and `POST /api/demo/reset` is expensive.
- [ ] **Real authentication and accounts.** The gate above is a shared secret,
      not a user model — see Product below.
- [ ] **Content-key custody.** The key currently lives in the listing process's
      memory. It needs escrowing somewhere durable that still cannot release it
      before escrow funds, and a defined recovery path when the seller's process
      dies mid-sale.
- [ ] **Encrypt memory at rest.** SQLite stores are plaintext on disk.

### Correctness

- [x] **An Evaluator agent for the arbiter role.** Built — `evaluator.py`. It
      re-runs the export pipeline over the buyer's own store rather than
      checking a number it was handed, signs a domain-separated verdict, and
      settles as the contract's arbiter with its own root. Receipts record
      `confirmed_by` so a buyer's self-report never reads as an independent
      check. **Still open:** the buyer can deny the evaluator access to their
      store, in which case the escrow expires back to them and nobody is paid —
      correct, but it means the evaluator is opt-in rather than enforced. Making
      access a condition of the key release is the next step.
- [ ] **Dispute resolution.** What happens when buyer and seller disagree after
      settlement. Currently: nothing.
- [ ] **Idempotent settlement recovery.** If the process dies between
      `confirmTransfer` landing and the off-chain seal, the seller is unsealed
      against a completed sale. Needs a reconciler that replays from chain
      events.
- [ ] **Handle chain reorgs.** Settlement is treated as final on receipt.
- [ ] **Gas and fee estimation**, with a ceiling and a retry policy.
- [ ] **Large-store performance.** The pipeline holds the whole package in
      memory and hashes it in one pass. Fine at 8 KB; unknown at 500 MB. Needs
      streaming export, chunked hashing, and a measured ceiling.
- [ ] **Concurrency.** Two exports of one tenant during a write are untested.
      Needs a snapshot boundary.

### Product

- [ ] **Real authentication and accounts.** There is no notion of a user. A
      connected wallet is now an *address*, not an account — nothing is
      authorised against it server-side.
- [x] **Multi-listing marketplace.** Six listings, each a real export, sortable
      and filterable by vertical, state, valuation, price and spread.
- [ ] **Watchlists and search** across the marketplace.
- [ ] **Seller onboarding** — connect a store, walk the redaction pass, preview
      what a buyer will see before committing.
- [ ] **A redaction review UI.** Flags are still set in code, but the listing
      flow now *reads* them: the scope selector greys out and disables any
      category with nothing sellable in it, from the data room's per-category
      transferability report. Setting the flags is what remains.
- [ ] **Notifications** — listing sold, escrow funded, transfer verified,
      confirmation window expiring.
- [ ] **Fiat on-ramp** or a clear statement that this is crypto-native only.

### Operations

- [ ] **Observability.** No metrics, traces or structured logs anywhere.
- [ ] **Alerting** on failed settlements, expired escrows and seal failures.
- [ ] **Backups** of seal registry and settlement state. Losing the seal
      registry means sold agents become writable again.
- [ ] **Runbook** for a stuck transfer, a failed seal, and a disputed sale.
- [ ] **Staging environment** on Base Sepolia, separate from local.

## P2 — Blocks general availability

### Legal and compliance

- [ ] **Counterparty data transfer.** The unresolved question: under what terms
      can records describing real customers move with a sale? Needs an answer
      grounded in the operator's own terms of service, and probably a consent
      mechanism for the counterparties themselves. This is the single largest
      non-technical risk in the project.
- [ ] **GDPR/CCPA.** Right to erasure versus an immutable hash commitment is a
      genuine conflict. Likely resolution: commit to salted hashes of erasable
      records so deletion does not invalidate the tree.
- [ ] **Terms of service, privacy policy, and a seller warranty** about what
      they are entitled to sell.
- [ ] **Tax treatment** of memory-asset sales.
- [ ] **Sanctions screening** on both wallets.

### The lifecycle primitives

| Primitive | State | Work |
|---|---|---|
| Sell | Built | — |
| Partial succession | Built | — |
| Archive | Free | Sibyl's own semantics at tenant level |
| **Lease** | Designed | A scheduled re-seal of the buyer's tenant, or an on-chain expiry a reader checks |
| **Conditional** | Designed | An oracle-style condition gate before the key releases |
| **Inherit** | Roadmap | The same pipeline, different trigger, no price discovery |
| **Merge** | Roadmap | Two evolved memories and a conflict rule for colliding `(category, name)` keys. Its own project. |
| **Split** | Roadmap | The inverse of merge; reuses the category filtering |
| **Revoke** | Roadmap | Depends on lease existing first |

### Protocol maturity

- [ ] **A second memory engine implementing SMP.** The strongest possible proof
      this is a protocol and not a Sibyl feature. Nothing above the adapter layer
      needs to change; write a second `MemorySource`/`MemorySink`.
- [ ] **Version and migrate the SMP format.** It is `1.0` with no migration path.
- [ ] **Publish the format** for independent implementation.
- [ ] **Reference test vectors** so another implementation can prove
      conformance.
- [ ] **Mainnet deployment** on Base, after audit.

## P3 — The protocol thesis

- [ ] **Memory reputation.** A memory asset developing its own reputation across
      lineages — successful inheritances, post-hoc buyer satisfaction, integrity
      record. Needs real transaction volume; faking it is exactly the pattern the
      rubric penalises.
- [ ] **Demand-based valuation.** The `buyer_demand`, `origin_reputation` and
      `buyer_satisfaction` terms, once a marketplace exists to compute them from.
- [ ] **Cross-engine lineage.** Provenance chains spanning different memory
      engines.
- [ ] **Fractional ownership** of a memory asset.
- [ ] **Memory-collateralised lending.** The customer book as collateral is the
      natural consequence of making it property.

---

## Known technical debt

Small, specific, and worth writing down before it is forgotten.

- [ ] `service/app.py` holds the listing envelope and content key in process
      memory, so a restart loses an *in-flight* sale. Needs durable storage —
      with the constraint that the content key must still be unreleasable
      before escrow funds, which is why it is not simply written next to the
      ciphertext. A *settled* sale now survives a restart: the outcome and its
      certificate are persisted under the workdir and served from
      `GET /api/listing/outcome`.
- [ ] The recorded-run artifact is regenerated manually. It should be a CI step,
      so it cannot drift from the pipeline it claims to record.
- [ ] `npm audit` reports three findings in `web` and two in `contracts`, all in
      build tooling (vite, esbuild, postcss, solc). `npm audit --omit=dev` is
      clean, so none of them reach a browser. Clearing them needs
      `npm audit fix --force`, which is a major version bump of the build chain;
      deliberately deferred rather than done days before a deadline, and worth
      doing immediately after.
- [ ] The service must run with a single worker: envelopes and content keys are
      held in process memory by design, so a second worker serves 409s for a
      listing it cannot see. Documented in `service/README.md`; the real fix is
      the durable envelope storage above.
- [ ] `contracts/compile.js` exists because Foundry could not be installed in the
      build environment. Both toolchains now run green in CI, so one of the two
      paths could go — but the py-evm suite is what executes where Foundry is
      unavailable, and the Foundry suite reaches things only a cheatcode can, so
      keeping both is a deliberate cost rather than an oversight.
- [ ] The agent's stopword list is hand-maintained. It works for freight; another
      domain would want a different one, or none.
- [ ] `_prune_dangling_relations` is O(n) per record against a set built each
      call. Fine at 49 records, not at 49,000.
- [ ] The wallet stack is its own bundle chunk, but still ships on first load
      because `WagmiProvider` wraps the whole app. Mounting it only in on-chain
      mode would save ~85 KB gzipped for every visitor in recorded mode, at the
      cost of remounting the tree when a deployment appears.
- [ ] The web app's route handling is a single path check. A third destination
      justifies a router.
- [ ] No E2E test drives the browser against the live service — the Playwright
      passes are manual. (The Part 9 rebuild was verified this way: list, fund,
      deliver, settle, screenshot. It should be a CI job, not a habit.)
- [ ] The frontend re-implements `listing_id_to_bytes32` in TypeScript because
      it builds its own calldata. Shared vectors are pinned in
      `test_listing_id_encoding_vectors`, but a shared fixture file would be
      better than two implementations agreeing by test.
- [ ] `demokeys.py` ships hardcoded keys. They are worthless and documented as
      such, but a production build should not compile them in at all.
