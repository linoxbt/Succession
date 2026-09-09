# Succession video demo script

Target length: 6–8 minutes. Use four named terminal tabs: `STATUS`, `SELLER`,
`EVALUATOR`, and `BUYER`. Put wallet keys in each tab before recording, clear
the screen, and never open `.env` or run `env` during the recording.

Replace `YOUR_AGENT_ID` and `listing-YOUR_ID` in advance. The agent must be
owned by the seller wallet on Base Sepolia, the buyer needs test USDC and ETH,
and the evaluator needs enough ETH for settlement gas.

## 00:00 — Product and dashboard

**Screen:** Open the deployed site, select **Dashboard**, and pause on the four
status cards.

**Say:**

> Succession makes an AI agent's accumulated memory portable and transferable.
> The dashboard is an operator view: it checks the hosted API, Base Sepolia
> contract, settlement mode, and confirmation policy. Wallet keys never enter
> this browser.

Point out the listing contract, ERC-8004 registry, payment token, and evaluator
address. Then open **Guide** briefly to show the three-role workflow.

## 00:45 — Preflight

**Terminal:** `STATUS`

```bash
cd /root/succession
git status --short
git log -1 --oneline
.venv/bin/succession status
.venv/bin/succession audit
```

**Expected:** a clean checkout, the release commit, configured service/chain
details, and a passing seven-claim local audit.

**Say:**

> The self-audit needs no wallet and moves a deterministic memory package
> through export, import, and verification. It establishes the local data path
> before we spend gas.

## 01:30 — Verify the live hosts

```bash
curl -s https://succession-production-7320.up.railway.app/api/health
curl -s https://succession-production-7320.up.railway.app/api/chain | python3 -m json.tool
```

**Expected:** `status: ok`, `mode: chain`, chain ID `84532`, a current head
block, and contract `0x642dFC05C9DCC0617c67B318C78dd5AE94134603`.

**Say:**

> The web status is not hard-coded decoration. These are the same live API
> responses rendered by the dashboard.

## 02:00 — Prove the seller's memory

**Terminal:** `SELLER`

```bash
.venv/bin/succession inventory --db seller.db --tenant seller-agent
.venv/bin/succession prove --db seller.db --tenant seller-agent \
  --agent erc8004:84532:YOUR_AGENT_ID
```

**Expected:** category counts, withheld records, and matching source and
destination roots from the isolated round trip.

**Say:**

> Inventory makes disclosure explicit. Prove exports the selected records,
> imports them into a separate temporary store, re-exports them, and compares
> every category root. Nothing has been listed and no buyer exists yet.

## 02:50 — Commit the package

The seller key must already exist in this terminal's environment.

```bash
.venv/bin/succession list --db seller.db --tenant seller-agent \
  --agent erc8004:84532:YOUR_AGENT_ID --price 1000000
```

Copy the printed listing ID into the prepared `EVALUATOR` and `BUYER` commands.
Show the transaction hash in BaseScan, then return to the terminal.

**Say:**

> The seller created and encrypted the package locally before broadcasting.
> The transaction commits its signed Merkle root and opens one USDC of escrow.
> The commitment now predates delivery.

## 03:35 — Buyer funds escrow

**Terminal:** `BUYER`

```bash
.venv/bin/succession show --listing listing-YOUR_ID
.venv/bin/succession buy --listing listing-YOUR_ID
.venv/bin/succession buy --listing listing-YOUR_ID --yes
```

The first `buy` is the dry run. The second explicitly approves USDC if needed
and funds escrow.

**Say:**

> The buyer reviews aggregate metadata and the committed root before paying.
> Broadcasting requires an explicit yes. The buyer still cannot collect
> plaintext because only the independent evaluator receives the pre-settlement
> key.

## 04:20 — Seller releases; evaluator decides

**Terminal:** `SELLER`

```bash
.venv/bin/succession fulfil --listing listing-YOUR_ID --once
```

**Terminal:** `EVALUATOR`

```bash
.venv/bin/succession evaluate --listing listing-YOUR_ID \
  --db evaluator.db --tenant isolated --yes
```

**Expected:** the evaluator reports signature validity, a matching committed
root, an imported destination root, and a settlement transaction hash.

**Say:**

> The evaluator runs with separate key custody and a separate database. It
> authenticates the seller, decrypts and imports the package, then derives the
> root from its own destination store. Its verdict atomically releases payment,
> transfers ERC-8004 identity, and seals the on-chain sale.

## 05:15 — Buyer claims and re-verifies

**Terminal:** `BUYER`

```bash
.venv/bin/succession claim --listing listing-YOUR_ID \
  --db buyer.db --tenant successor
.venv/bin/succession inventory --db buyer.db --tenant successor
```

**Say:**

> Only after evaluator settlement can the buyer collect the content key. Claim
> imports transactionally, re-hashes the buyer's store, and writes a durable
> acquisition certificate. The final inventory is read from that new store.

## 06:00 — Demonstrate restart recovery

Stop and restart the seller watcher or open fresh terminal processes. Repeating
these commands uses the existing durable vault and buyer journal:

```bash
# Seller host
.venv/bin/succession fulfil --listing listing-YOUR_ID --once

# Buyer host, with the same destination
.venv/bin/succession claim --listing listing-YOUR_ID \
  --db buyer.db --tenant successor

# Final evidence
.venv/bin/succession audit --check-chain
```

**Expected:** no duplicate import or duplicate settlement; the final audit
matches published roots to Base Sepolia commitments.

**Say:**

> Recovery is replay-safe. The seller reconstructs relay state from its local
> vault, while the buyer completes from its destination journal. The release
> waits for three Base Sepolia confirmations. For mainnet, the policy calls for
> L1-finalized reconciliation before irreversible retirement outside the
> contract.

## Closing shot

Return to **Terminal demo** in the web app.

**Say:**

> Succession demonstrates the full custody boundary: seller commitment before
> delivery, independent evaluation before key collection, destination re-hash,
> atomic on-chain settlement, and recoverable off-chain progress. Every claim
> shown here can be repeated from these commands.
