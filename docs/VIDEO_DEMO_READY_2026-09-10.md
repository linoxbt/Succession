# Ready Base Sepolia video demo

This pair is registered and deliberately left unlisted so the transfer can be
performed live while recording.

| Field | Value |
|---|---|
| Origin agent | `erc8004:84532:0694` — Succession video origin |
| Successor agent | `erc8004:84532:0695` — Succession video successor |
| Listing to create | `listing-694` |
| Price | `1000000` minor units — 1 test USDC |
| Listing contract | `0x642dFC05C9DCC0617c67B318C78dd5AE94134603` |
| ERC-8004 registry | `0x7177a6867296406881E20d6647232314736Dd09A` |
| Seller store | `video-demo-ready/seller.db`, tenant `video-seller` |
| Buyer store | `video-demo-ready/buyer.db`, tenant `video-successor` |
| Evaluator store | `video-demo-ready/evaluator.db`, tenant `video-evaluator` |

The origin store contains 49 sellable records across all six categories. A
local round trip produced matching root
`0xabe7754b7c2a0f0b4408f3347f00b56858d3637185b41846fd1f3d7f9c0beee1`.
The buyer and evaluator stores are empty. The listing does not yet exist.

Open four terminals named `STATUS`, `SELLER`, `BUYER`, and `EVALUATOR`. In each
terminal, run this before recording, then clear the screen:

```bash
cd /root/succession
set -a; source .env; set +a
export SUCCESSION_MARKETPLACE=https://succession-production-7320.up.railway.app
```

In `SELLER`, also prepare the role-specific variable:

```bash
export SUCCESSION_SIGNING_KEY="$SELLER_PRIVATE_KEY"
```

In `BUYER`:

```bash
export SUCCESSION_BUYER_KEY="$BUYER_PRIVATE_KEY"
```

The evaluator already reads `SUCCESSION_EVALUATOR_KEY` from the loaded file.
Never show `.env`, `env`, `printenv`, or private-key values while recording.

## Commands to record

`STATUS` — show the seeded origin and deterministic local proof:

```bash
.venv/bin/succession inventory --db video-demo-ready/seller.db --tenant video-seller
.venv/bin/succession prove --db video-demo-ready/seller.db --tenant video-seller \
  --agent erc8004:84532:0694
```

`SELLER` — commit the signed memory root and publish the encrypted package:

```bash
.venv/bin/succession list --db video-demo-ready/seller.db --tenant video-seller \
  --agent erc8004:84532:0694 --price 1000000
```

`BUYER` — inspect the listing, preview the transaction, then fund escrow:

```bash
.venv/bin/succession show --listing listing-694
.venv/bin/succession buy --listing listing-694
.venv/bin/succession buy --listing listing-694 --yes
```

`SELLER` — release the content key after escrow is visible:

```bash
.venv/bin/succession fulfil --listing listing-694 --once
```

`EVALUATOR` — show the independent verdict first, then submit it:

```bash
.venv/bin/succession evaluate --listing listing-694 \
  --db video-demo-ready/evaluator.db --tenant video-evaluator
.venv/bin/succession evaluate --listing listing-694 \
  --db video-demo-ready/evaluator.db --tenant video-evaluator --yes
```

`BUYER` — claim into the successor store and name agent 695 in the certificate:

```bash
.venv/bin/succession claim --listing listing-694 \
  --db video-demo-ready/buyer.db --tenant video-successor \
  --successor-agent erc8004:84532:0695
.venv/bin/succession inventory --db video-demo-ready/buyer.db --tenant video-successor
```

`STATUS` — close on the chain-backed audit:

```bash
.venv/bin/succession audit --check-chain
```

Settlement moves origin identity token 694 from the seller wallet to the buyer
wallet, releases escrow to the seller, seals that origin identity, and imports
the verified package into the store assigned to successor agent 695. The
certificate records `origin_agent` 694 and `successor_agent` 695.

## Registration evidence

- Origin registration: `0x807e346d9123ab5660582e12ef5aca57a4a55a8aa8b0fe87873931968ef273bf`
- Successor registration: `0xc7aa51b72446b2088589bf9aef0c2a14d389bfea5e12dd7978b56831ecd6d4a0`

The separate completed acceptance record in
`deployments/demo-video-completed.json` proves the same workflow with origin
agent 692 and successor agent 693. It transferred 49 records with matching
committed and destination roots in settlement transaction
`0xec4c2dddbc9378b6da0f9f574fb5636523d98af603bbf1777cbd9d2927704737`.
