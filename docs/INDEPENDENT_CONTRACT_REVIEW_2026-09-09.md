# Independent contract review — 9 September 2026

## Scope and independence boundary

This review covers `contracts/src/ListingContract.sol` and its interfaces and
mocks at the source deployed to Base Sepolia on 9 September 2026. It combines a
fresh Slither 0.11.5 run, manual state-machine and trust-boundary review, the
Foundry suite, and an exact comparison of the deployment transaction input with
the compiled creation bytecode and constructor arguments.

This is an independent automated/manual review pass performed outside the
implementation flow. It is **not** a third-party professional audit, formal
verification, or assurance for mainnet funds. An external audit remains prudent
before accepting customer assets or material value.

## Result

No unresolved critical, high, or medium-severity contract defect was found in
the reviewed scope. The review added constructor checks that reject zero or EOA
payment-token and identity-registry dependencies. The final Foundry suite passes
31 tests, including 256 fuzz cases.

The deployed creation input matches the locally compiled optimized solc 0.8.28
bytecode and these constructor arguments exactly:

- payment token: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- identity registry: `0x7177a6867296406881E20d6647232314736Dd09A`
- evaluator: `0x518477058d12e60D74E42b799F5ad0f5c4FFf31b`

The live runtime is 6,517 bytes with hash
`f6180b8abc84c730a545f636515f5d451713756b8506e680ad9be1db3b8c1240`.

## Slither findings and disposition

Slither analyzed three contracts with 101 detectors and reported eight items:

| Detector | Count | Disposition |
|---|---:|---|
| arbitrary-send-erc20 | 1 | False positive caused by the ERC-721 `transferFrom(seller,buyer,agentId)` signature. The seller and token id come from the listing; ownership and approval are checked when listing and enforced again by the registry during settlement. |
| reentrancy-balance | 1 | Accepted. `buy` moves the listing to `Escrowed` before token interaction, so re-entry into `buy` fails its state guard. The transaction reverts on any balance-delta mismatch. The production token is validated as Circle's six-decimal USDC. |
| reentrancy-events | 3 | Accepted. Settlement/refund state, escrow balance, active listing and seal effects are written before interaction. A failed external call reverts all effects; emitted events describe only completed calls. |
| timestamp | 2 | Intentional use for the seven-day escrow deadline. Small timestamp influence cannot redirect funds and expiry only returns the recorded escrow to the recorded buyer. The reported balance comparison is not timestamp-dependent. |
| assembly | 1 | Accepted standard 65-byte ECDSA decoding. Recovery rejects non-27/28 `v`, high-`s`, wrong length and signatures that do not recover to the seller. |

## Manual checks

- Only the immutable evaluator can confirm either release or hash-mismatch
  refund. Buyer-controlled false mismatch settlement is unavailable.
- The contract measures the payment balance delta and accounts escrow per
  listing, preventing fee-taking tokens or pooled funds from shorting a seller.
- Identity transfer and payment occur in one transaction after state effects;
  either external failure reverts the entire settlement.
- Attestations bind chain id, contract, listing id, agent id and commitment and
  enforce canonical ECDSA encoding.
- One active listing per identity prevents double-funded competing sales.
- Cancel, bilateral refund and permissionless post-deadline reclaim all clear
  the active pointer and return only that listing's escrow.

## Residual trust and operational risks

The evaluator is a trusted confidential role. Its compromise can expose a
delivered package or approve a matching-root package without applying an
operator's intended policy. The immutable key cannot be rotated in this
contract, so rotation requires a new deployment and migration of new listings.
The contract cannot erase seller files or revoke credentials outside the
protocol. Base Sepolia transactions and test USDC are acceptance evidence, not
mainnet assurance.
