/**
 * GENERATED FILE, do not edit.
 *
 * Produced by `node scripts/generate-abi.mjs` from the compiled
 * `contracts/out/artifacts.json`, so the ABI the browser sends can never drift
 * from the Solidity that was deployed. Re-run the script after changing
 * ListingContract.sol; CI fails if this file is stale.
 *
 * Custom errors are included in full: without them a revert surfaces as an
 * opaque hex selector instead of `WrongState` or `NotAuthorised`, and a buyer
 * staring at 0x1f2a3b4c has no idea whether to retry or walk away.
 */

export const LISTING_ABI = [
  {
    "inputs": [
      {
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      }
    ],
    "name": "AgentAlreadyListed",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "AgentAlreadySealed",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "BadAttestation",
    "type": "error"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "expected",
        "type": "uint256"
      },
      {
        "internalType": "uint256",
        "name": "received",
        "type": "uint256"
      }
    ],
    "name": "EscrowShortfall",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "ListingExists",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "NoSuchListing",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "NotAgentOwner",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "NotAuthorised",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "RegistryNotApproved",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "SelfPurchase",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "TransferFailed",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "WindowNotElapsed",
    "type": "error"
  },
  {
    "inputs": [
      {
        "internalType": "enum ListingContract.State",
        "name": "expected",
        "type": "uint8"
      },
      {
        "internalType": "enum ListingContract.State",
        "name": "actual",
        "type": "uint8"
      }
    ],
    "name": "WrongState",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "ZeroCommitment",
    "type": "error"
  },
  {
    "inputs": [],
    "name": "ZeroPrice",
    "type": "error"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "uint256",
        "name": "agentId",
        "type": "uint256"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "formerOwner",
        "type": "address"
      },
      {
        "indexed": false,
        "internalType": "bytes32",
        "name": "verifiedHash",
        "type": "bytes32"
      }
    ],
    "name": "AgentSealed",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "buyer",
        "type": "address"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      }
    ],
    "name": "Escrowed",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "buyer",
        "type": "address"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amount",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "string",
        "name": "reason",
        "type": "string"
      }
    ],
    "name": "Refunded",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {
        "indexed": true,
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      },
      {
        "indexed": true,
        "internalType": "address",
        "name": "buyer",
        "type": "address"
      },
      {
        "indexed": true,
        "internalType": "uint256",
        "name": "agentId",
        "type": "uint256"
      },
      {
        "indexed": false,
        "internalType": "bytes32",
        "name": "verifiedHash",
        "type": "bytes32"
      },
      {
        "indexed": false,
        "internalType": "uint256",
        "name": "amountReleased",
        "type": "uint256"
      }
    ],
    "name": "TransferConfirmed",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "CONFIRMATION_WINDOW",
    "outputs": [
      {
        "internalType": "uint64",
        "name": "",
        "type": "uint64"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "arbiter",
    "outputs": [
      {
        "internalType": "address",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      }
    ],
    "name": "buy",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      },
      {
        "internalType": "bytes32",
        "name": "deliveredHash",
        "type": "bytes32"
      }
    ],
    "name": "confirmTransfer",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "bytes32",
        "name": "listingId",
        "type": "bytes32"
      }
    ],
    "name": "getListing",
    "outputs": [
      {
        "components": [
          {
            "internalType": "address",
            "name": "seller",
            "type": "address"
          },
          {
            "internalType": "address",
            "name": "buyer",
            "type": "address"
          },
          {
            "internalType": "uint256",
            "name": "agentId",
            "type": "uint256"
          },
          {
            "internalType": "bytes32",
            "name": "hashCommitment",
            "type": "bytes32"
          },
          {
            "internalType": "uint256",
            "name": "price",
            "type": "uint256"
          },
          {
            "internalType": "uint64",
            "name": "escrowDeadline",
            "type": "uint64"
          },
          {
            "internalType": "enum ListingContract.State",
            "name": "state",
            "type": "uint8"
          },
          {
            "internalType": "bytes32",
            "name": "deliveredHash",
            "type": "bytes32"
          },
          {
            "internalType": "uint256",
            "name": "escrowed",
            "type": "uint256"
          }
        ],
        "internalType": "struct ListingContract.Listing",
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "identityRegistry",
    "outputs": [
      {
        "internalType": "contract IIdentityRegistry",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "uint256",
        "name": "agentId",
        "type": "uint256"
      }
    ],
    "name": "isSealed",
    "outputs": [
      {
        "internalType": "bool",
        "name": "",
        "type": "bool"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "paymentToken",
    "outputs": [
      {
        "internalType": "contract IERC20",
        "name": "",
        "type": "address"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  }
] as const;

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
