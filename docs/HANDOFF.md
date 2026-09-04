# Handoff prompt — run the network-blocked work locally

Everything below was built and tested in an environment whose egress policy
blocks Base RPCs, Virtuals, and Netlify. The code paths are complete; what is
missing is credentials and a network route.

Copy the block below into Claude Code on a machine with normal internet.

---

```
You are picking up the Succession project. It is complete in code and blocked
only on network access and credentials, which this machine has and the build
environment did not.

REPO      https://github.com/linoxbt/Succession
BRANCH    claude/session-3993th   (work on this branch, push to it)
STATE     183 tests passing, web build clean, nothing deployed anywhere

Read these first, in this order. They are accurate and were written for you:
  README.md                     what the system is and how it settles
  docs/ROADMAP.md               the P0 list — your job is the P0 section
  docs/sibyl-setup.md           memory setup and the submission answers
  scripts/finish_integrations.sh  the sequence, with preflight checks

Deadline: the Sibyl Labs Hackathon closes 10 September 2026.

=== GROUND RULES — these are not negotiable ===

1. NEVER fabricate a number, hash, transaction, job record or screenshot.
   Every figure this project displays is computed from a real export of a real
   store. If something cannot be produced for real, say so and leave it out.
   The judging rubric explicitly penalises "smoke and mirrors", and the whole
   thesis is that the claims are checkable.

2. NEVER substitute LocalSettlement for the chain in anything presented as a
   result. It mirrors the contract's state machine for tests and offline work.
   Using it while implying a real settlement is the one dishonest thing
   available in this codebase.

3. If IDENTITY_REGISTRY_ADDRESS is unset the deploy uses an ERC-721 stand-in
   and writes identity_registry_is_mock: true. Do not hide that flag, and do
   not describe the result as an ERC-8004 transfer if it is set.

4. Report blockers plainly rather than working around them. A missing faucet
   or an unregistered agent is information, not a problem to route around.

=== STEP 1 — Sibyl Memory, Pro tier ===

  pip install 'sibyl-memory-cli[mcp]'
  sibyl init      # opens a browser; sign in with email or wallet
  sibyl setup     # wires up Claude Code — restart after
  sibyl status    # confirm the tier and the store path

Paste the `sibyl status` output back so the tier is on record.

=== STEP 2 — Virtuals ACP registration (DO THIS FIRST of the two chains) ===

ACP will not let an unregistered agent be discovered or hired, so this gates
everything downstream. It is done in the Virtuals app, not by an SDK call.

  Follow the ACP Tech Playbook:
  https://whitepaper.virtuals.io/info-hub/builders-hub/agent-commerce-protocol-acp-builder-guide/acp-tech-playbook

  Register TWO agents (a seller and a buyer). Registration issues a
  whitelisted wallet and an entity id. Then:

  export WHITELISTED_WALLET_PRIVATE_KEY=0x...
  export AGENT_WALLET_ADDRESS=0x...
  export ACP_ENTITY_ID=...

  .venv/bin/python -m succession.acp_cli status        # must show registered: true
  .venv/bin/python -m succession.acp_cli snapshot --out web/public/acp-snapshot.json
  .venv/bin/python -m succession.acp_cli sync --db <seller.db> --tenant <tenant>

The agent needs REAL completed ACP jobs for the earnings signal to mean
anything — the valuation needs at least 5 resolved outcomes before it will use
ACP over the journal heuristic, and below that it correctly falls back. If the
agents have no job history yet, run some real ACP jobs between them first. Do
not seed fake ones.

Verify: the console's Agents tab shows completed jobs with on-chain job ids,
and the Marketplace's "Verifiable earnings" tile stops reading 0/6.

=== STEP 3 — Base Sepolia ===

  Fund a deployer key: https://docs.base.org/get-started/get-funds

  export BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
  export DEPLOYER_PRIVATE_KEY=0x...
  export SELLER_PRIVATE_KEY=0x...        # must hold the ERC-8004 identities
  export BUYER_PRIVATE_KEY=0x...         # must hold the payment token
  export IDENTITY_REGISTRY_ADDRESS=0x... # a real ERC-8004 registry, if you have one

  # Prove the scripts work against an in-process EVM first — costs nothing:
  .venv/bin/python scripts/deploy_base_sepolia.py --local
  .venv/bin/python scripts/run_transfers.py --local --count 5

  # Then for real:
  ./scripts/finish_integrations.sh

That script preflights the keys, the RPC's reachability and every wallet
balance before it spends anything. If you prefer the steps separately:

  .venv/bin/python scripts/deploy_base_sepolia.py
  .venv/bin/python scripts/run_transfers.py --count 5 --corrupt 3

--corrupt 3 deliberately corrupts the third transfer so the refund path is
demonstrated too. Keep it. Five successes prove the happy path and say nothing
about whether the buyer's protection works.

Expected: 4 verified, 1 refunded. Anything else is a real failure — debug it,
do not re-run until it looks good.

Then verify the contract on Basescan so a judge can read the source at the
address, and paste the contract address and the five transaction hashes back.

=== STEP 4 — Fold the real results into the UI ===

  .venv/bin/python scripts/record_run.py

This regenerates web/public/recorded-run.json and folds
deployments/transfers.json in, so the console's Transfers view shows the real
Base Sepolia transactions instead of an empty table. Confirm the transaction
hashes in the UI match the ones on Basescan.

=== STEP 5 — Deploy the site ===

The Netlify project already exists:
  name     succession-memory
  site id  8518ba9f-c4cd-464a-b415-eb7ef6d2284a

netlify.toml is complete (base web/, publish dist, SPA fallback, CSP, cache
headers). Link the repo under Site configuration → Build & deploy → Continuous
deployment, branch claude/session-3993th. Nothing needs configuring in the UI.

If the service is deployed somewhere too (Railway/Render/Fly — Netlify cannot
run FastAPI), uncomment the /api/* proxy block in netlify.toml and point it at
that host. Otherwise the site correctly runs in recorded mode with a banner
saying so.

Verify the deployed URL loads, the marketplace shows six listings, and the
recorded banner is either present and accurate or gone because a live service
is reachable.

=== STEP 6 — The two-machine rehearsal ===

Not simulate-able with two browser tabs, and the spec is explicit about it.
Seller and buyer on genuinely separate hosts, passing the SMP package as a
file:

  # machine A
  SUCCESSION_SIGNING_KEY=0x... .venv/bin/python -m succession.cli export \
    --db seller.db --tenant t-seller --agent erc8004:84532:0417 --out pkg

  # machine B, after copying pkg across
  .venv/bin/python -m succession.cli verify pkg --root 0x... --signer 0x...
  .venv/bin/python -m succession.cli import pkg --db buyer.db --tenant t-buyer \
    --root 0x... --signer 0x...

Do it twice before recording. Include the sealed-write rejection.

=== STEP 7 — Film the demo (2–5 minutes) ===

Must include the fresh-session recall beat. `python -m succession.demo` prints
the beats in order with real output; docs/ROADMAP.md P0 lists what the
submission needs. Keep the hash comparison on screen — it is the credibility.

=== WHAT TO DO WHEN YOU FINISH EACH STEP ===

Commit and push to claude/session-3993th. Update the status table in README.md
("Built; not yet deployed" → the real state) and tick the P0 items in
docs/ROADMAP.md as they genuinely complete. Do not tick anything you have not
actually verified.

Run the full suite before every push:
  .venv/bin/python -m pytest packages/succession/tests
  ( cd web && npm run build )

=== IF SOMETHING IS BLOCKED ===

Tell me which host, which credential, or which step, and stop. Do not
substitute local settlement, do not generate placeholder job history, and do
not mark a roadmap item done because the code for it exists. The value of this
project is that its claims are checkable; a shortcut here costs more than the
missing feature.
```

---

## Hosts that were blocked, for reference

Confirmed by the build environment's proxy as `403 to CONNECT (policy denial)`:

| Host | Blocked |
|---|---|
| `sepolia.base.org` and 10 other Base Sepolia RPC providers | Deploy, transfers |
| `acpx.virtuals.gg`, `alchemy-proxy.virtuals.io` | ACP registration and job history |
| `api.netlify.com`, `app.netlify.com`, `*.netlify.app` | Site deploy |
| `www.micro1.ai` | Landing-page reference |
| `hack.sibyllabs.org` | Hackathon rubric detail |
| `foundry.paradigm.xyz` | `forge` install (solc used instead) |

PyPI and npm were reachable throughout, so the dependency tree is complete.
