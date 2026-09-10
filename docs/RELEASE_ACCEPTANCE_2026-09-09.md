# Release acceptance — 9 September 2026

## Coordinated release

| Component | Release |
|---|---|
| Listing contract | Base Sepolia `0x642dFC05C9DCC0617c67B318C78dd5AE94134603` |
| Deployment transaction | `0xa1a73112ea9c9dcb87bf29c26098e91e9ca9f9812a7b623c7a75e796acd03357`, block `46599979` |
| Marketplace API | `https://succession-production-7320.up.railway.app` |
| Frontend | `https://web-gray-xi-95.vercel.app` |
| Evaluator | `0x518477058d12e60D74E42b799F5ad0f5c4FFf31b` |

The contract deployment input exactly matched the reviewed optimized solc
0.8.28 creation bytecode and constructor arguments. Read-back confirmed 6,517
runtime bytes, the expected USDC and ERC-8004 registry immutables, and the
dedicated evaluator. Railway runs the Docker service with a persistent `/data`
volume and three-confirmation policy. Vercel serves the Vite application and
proxies same-origin `/api` requests to that service.

## Live transaction acceptance

`deployments/transfers.json` records five new sales on this contract. Four
matching evaluator deliveries released payment and transferred distinct origin
identities. Transfer 3 intentionally changed one delivered value; the evaluator
derived a different root and transaction
`0x8d00acaa02c8aa2059ded1ab28b432673f29dddde799190be08bdcee8a921ca5`
refunded the buyer without moving or sealing the identity.

The live flow used four distinct EOAs for deployer, seller, buyer and evaluator.
The buyer approved Circle Base Sepolia USDC and funded escrow. The evaluator key
was generated into the ignored mode-600 operator environment and funded with
only 0.003 test ETH. No private key was uploaded to Railway or Vercel.

## Two-host interruption and recovery

The recovery acceptance used the Railway host and separate seller, evaluator
and buyer processes with isolated local databases:

1. The seller relisted refunded identity `erc8004:84532:0686`, published its
   encrypted envelope, and retained the content key in its durable local vault.
2. The buyer approved and escrowed 1 test USDC.
3. The seller released the key, then the Railway service was deliberately
   restarted before evaluation. Persistent metadata survived; the transient
   relay key did not.
4. An authenticated evaluator request returned HTTP 404, proving the lost key
   was not fabricated or served from stale persistent state.
5. The seller watcher republished from its vault. The evaluator imported into
   its isolated store, matched the committed root and seller signature, then
   settled transaction
   `0x07978210269e15d46f8bd2b3fdfea10bdb3decb50d11dd245f90e964a46c279d`.
6. The buyer imported 49 records. Its first certificate completion uncovered a
   post-settlement event-cursor defect. The fix scans from `deployment_block`;
   the same durable journal then completed without a second import.

The complete machine-readable record is
`deployments/recovery-acceptance.json`.

## Finality policy

Base Sepolia writes and crash-recovered settlement receipts require three
confirmations. Buyer key release also reconstructs the matching settlement event
from the recorded deployment block and applies that depth. Local EVM runs use
one confirmation. This provides a practical testnet acceptance threshold; it is
not Ethereum L1 finality. Mainnet operation should reconcile against L1-finalized
state before irreversible external retirement and retain a replay/reindex plan
for deeper reorganizations.

## Review and remaining limits

[INDEPENDENT_CONTRACT_REVIEW_2026-09-09.md](INDEPENDENT_CONTRACT_REVIEW_2026-09-09.md)
records the Slither and manual contract pass. It is not a third-party
professional audit. The release verifies the EOA wallet path and local ERC-1271
behavior; browser provider popups and passkey wallets still need provider-specific
live acceptance. ERC-8004 registration and transfer were live; external Virtuals
ACP jobs were not exercised. Monitoring, capacity limits, backups and deeper L1
reorg reconciliation remain operational gates for customer or mainnet assets.
