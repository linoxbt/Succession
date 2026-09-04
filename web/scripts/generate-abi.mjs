/**
 * Generate the frontend's contract ABI from the compiled artifact.
 *
 * Hand-copying an ABI into the frontend is how a UI ends up calling a function
 * signature the deployed contract no longer has — the mismatch does not show up
 * at build time, it shows up as an unexplained revert with a buyer's money in
 * escrow. This reads `contracts/out/artifacts.json`, which `compile.js`
 * produces from the Solidity, so the two cannot drift.
 *
 *     node scripts/generate-abi.mjs
 *
 * CI runs it and fails if the committed output differs.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const artifacts = resolve(here, "../../contracts/out/artifacts.json");
const target = resolve(here, "../src/chain/abi.ts");

const all = JSON.parse(readFileSync(artifacts, "utf8"));

/** Only what the browser calls. A narrower ABI is a smaller bundle and a
 *  clearer statement of what this surface is allowed to do. */
const WANTED = new Set([
  "buy",
  "confirmTransfer",
  "getListing",
  "isSealed",
  "arbiter",
  "paymentToken",
  "identityRegistry",
  "CONFIRMATION_WINDOW",
  "Escrowed",
  "TransferConfirmed",
  "Refunded",
  "AgentSealed",
]);

const listing = all.ListingContract.abi.filter(
  (item) =>
    (item.type === "function" && WANTED.has(item.name)) ||
    (item.type === "event" && WANTED.has(item.name)) ||
    item.type === "error",
);

const banner = `/**
 * GENERATED FILE — do not edit.
 *
 * Produced by \`node scripts/generate-abi.mjs\` from the compiled
 * \`contracts/out/artifacts.json\`, so the ABI the browser sends can never drift
 * from the Solidity that was deployed. Re-run the script after changing
 * ListingContract.sol; CI fails if this file is stale.
 *
 * Custom errors are included in full: without them a revert surfaces as an
 * opaque hex selector instead of \`WrongState\` or \`NotAuthorised\`, and a buyer
 * staring at 0x1f2a3b4c has no idea whether to retry or walk away.
 */
`;

const body = `${banner}
export const LISTING_ABI = ${JSON.stringify(listing, null, 2)} as const;

/** The ERC-20 surface an escrow payment needs. USDC on Base Sepolia. */
export const ERC20_ABI = [
  {
    type: "function",
    name: "approve",
    stateMutability: "nonpayable",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
  },
  {
    type: "function",
    name: "allowance",
    stateMutability: "view",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    type: "function",
    name: "balanceOf",
    stateMutability: "view",
    inputs: [{ name: "account", type: "address" }],
    outputs: [{ name: "", type: "uint256" }],
  },
  {
    type: "function",
    name: "decimals",
    stateMutability: "view",
    inputs: [],
    outputs: [{ name: "", type: "uint8" }],
  },
  {
    type: "function",
    name: "symbol",
    stateMutability: "view",
    inputs: [],
    outputs: [{ name: "", type: "string" }],
  },
] as const;
`;

writeFileSync(target, body);
console.log(`wrote ${target} (${listing.length} ABI entries)`);
