/**
 * GENERATED FILE, do not edit.
 *
 * Produced by `python scripts/generate_reference.py` from the argparse parsers
 * in `succession/cli.py` and `succession/acp_cli.py`, so the guide in this app
 * cannot describe a command the tool does not have, or miss one it does.
 *
 * Before this existed the web app named five of nineteen commands and the
 * README omitted three. Both were written by hand.
 */

export interface CommandFlag {
  names: string[];
  required: boolean;
  help: string;
  choices: string[];
  positional: boolean;
}

export interface Command {
  name: string;
  help: string;
  flags: CommandFlag[];
}

export interface CommandGroup {
  title: string;
  note: string;
  commands: string[];
}

export interface EnvVar {
  name: string;
  help: string;
}

export interface Reference {
  succession: Command[];
  "succession-acp": Command[];
  env: EnvVar[];
  groups: CommandGroup[];
}

export const REFERENCE: Reference = {
  "succession": [
    {
      "name": "export",
      "help": "build and sign an SMP package",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--agent"
          ],
          "required": true,
          "help": "ERC-8004 identity, e.g. erc8004:84532:0417",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--out"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--categories"
          ],
          "required": false,
          "help": "partial succession: transfer only these",
          "choices": [
            "identity",
            "relationships",
            "preferences",
            "history",
            "commitments",
            "learned-behaviors"
          ],
          "positional": false
        }
      ]
    },
    {
      "name": "inspect",
      "help": "describe a package without importing it",
      "flags": [
        {
          "names": [
            "package"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": true
        }
      ]
    },
    {
      "name": "verify",
      "help": "check a package against a commitment",
      "flags": [
        {
          "names": [
            "package"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": true
        },
        {
          "names": [
            "--root"
          ],
          "required": true,
          "help": "the root committed on-chain",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--signer"
          ],
          "required": true,
          "help": "the seller's address",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "import",
      "help": "import a package into a fresh tenant",
      "flags": [
        {
          "names": [
            "package"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": true
        },
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--root"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--signer"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "value",
      "help": "compute the reference valuation",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "preview",
      "help": "compute the data-room preview",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--agent"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "list",
      "help": "list your agent's memory for sale, on chain",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--agent"
          ],
          "required": true,
          "help": "the ERC-8004 identity you hold, e.g. erc8004:84532:417",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--price"
          ],
          "required": true,
          "help": "asking price in the payment token's minor units (USDC has 6)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--categories"
          ],
          "required": false,
          "help": "partial succession: sell only these, in whole",
          "choices": [
            "identity",
            "relationships",
            "preferences",
            "history",
            "commitments",
            "learned-behaviors"
          ],
          "positional": false
        },
        {
          "names": [
            "--scope"
          ],
          "required": false,
          "help": "sell a share of each, e.g. relationships=60,history=100",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "publish",
      "help": "publish an already-listed agent to a marketplace",
      "flags": [
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the listing id to publish",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--vault"
          ],
          "required": false,
          "help": "seller vault directory (env: SUCCESSION_VAULT)",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "fulfil",
      "help": "release content keys once escrow is funded",
      "flags": [
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": false,
          "help": "just this one (default: all)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--interval"
          ],
          "required": false,
          "help": "seconds between polls",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--once"
          ],
          "required": false,
          "help": "check once and exit",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "claim",
      "help": "collect, import and verify memory you bought",
      "flags": [
        {
          "names": [
            "--auth-file"
          ],
          "required": false,
          "help": "single-use buyer authorization downloaded from the browser",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the listing you funded escrow on",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "evaluate",
      "help": "independently verify and settle an escrowed delivery",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the escrowed listing to evaluate",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--yes"
          ],
          "required": false,
          "help": "submit the signed verdict on chain",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "inventory",
      "help": "what this agent actually has to sell, per category",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "prove",
      "help": "prove every category transfers, against your own store",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "Sibyl store path",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "tenant id",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--agent"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--categories"
          ],
          "required": false,
          "help": "check only these (default: all six)",
          "choices": [
            "identity",
            "relationships",
            "preferences",
            "history",
            "commitments",
            "learned-behaviors"
          ],
          "positional": false
        },
        {
          "names": [
            "--scope"
          ],
          "required": false,
          "help": "prove a partial sale, e.g. relationships=60,history=100",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "market",
      "help": "what is for sale",
      "flags": [
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--state"
          ],
          "required": false,
          "help": "only listings in this state",
          "choices": [
            "open",
            "escrowed",
            "confirmed",
            "refunded"
          ],
          "positional": false
        },
        {
          "names": [
            "--json"
          ],
          "required": false,
          "help": "machine-readable output",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "show",
      "help": "one listing's data room, before paying",
      "flags": [
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the listing to inspect",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--json"
          ],
          "required": false,
          "help": "machine-readable output",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "buy",
      "help": "fund escrow for a listing",
      "flags": [
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the listing to fund",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--yes"
          ],
          "required": false,
          "help": "send the transactions rather than describing them",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "confirm",
      "help": "deprecated: buyers cannot settle delivery",
      "flags": [
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--db"
          ],
          "required": false,
          "help": "the database used by claim",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": false,
          "help": "the destination tenant used by claim",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--listing"
          ],
          "required": true,
          "help": "the listing to settle",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--root"
          ],
          "required": true,
          "help": "the root succession claim re-derived from your own store",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--yes"
          ],
          "required": false,
          "help": "send the transaction",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "status",
      "help": "what this installation is connected to",
      "flags": [
        {
          "names": [
            "--deployment"
          ],
          "required": false,
          "help": "path to the deployment record (default: deployments/base-sepolia.json)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--artifacts"
          ],
          "required": false,
          "help": "contract ABI json (env: SUCCESSION_ARTIFACTS)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--db"
          ],
          "required": false,
          "help": "a store to report on",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": false,
          "help": "which tenant, with --db",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "audit",
      "help": "check every claim this project makes about itself",
      "flags": [
        {
          "names": [
            "--marketplace"
          ],
          "required": false,
          "help": "marketplace base URL (env: SUCCESSION_MARKETPLACE)",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--check-chain"
          ],
          "required": false,
          "help": "also compare published roots to their on-chain commitments",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--json"
          ],
          "required": false,
          "help": "machine-readable output",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "listings",
      "help": "what you have listed",
      "flags": []
    }
  ],
  "succession-acp": [
    {
      "name": "status",
      "help": "confirm registration and show job history",
      "flags": [
        {
          "names": [
            "--snapshot"
          ],
          "required": false,
          "help": "read from a captured snapshot instead of the live API",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "sync",
      "help": "mirror ACP job history into a tenant's memory",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--snapshot"
          ],
          "required": false,
          "help": "read from a captured snapshot instead of the live API",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "snapshot",
      "help": "capture live job history to a file",
      "flags": [
        {
          "names": [
            "--out"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        }
      ]
    },
    {
      "name": "show",
      "help": "show the job history a tenant already carries",
      "flags": [
        {
          "names": [
            "--db"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        },
        {
          "names": [
            "--tenant"
          ],
          "required": true,
          "help": "",
          "choices": [],
          "positional": false
        }
      ]
    }
  ],
  "env": [
    {
      "name": "SUCCESSION_SIGNING_KEY",
      "help": "The seller's wallet. Read from the environment, never an argument, because a private key on a command line lands in shell history and in the process table."
    },
    {
      "name": "SUCCESSION_BUYER_KEY",
      "help": "The buyer's wallet. Deliberately a different variable from the seller's: conflating them is how someone tries to buy their own listing."
    },
    {
      "name": "SUCCESSION_EVALUATOR_KEY",
      "help": "The independent evaluator wallet configured in the listing contract. It alone may settle a delivery."
    },
    {
      "name": "SUCCESSION_FINALITY_CONFIRMATIONS",
      "help": "Receipt depth required before a chain write is accepted. Defaults to three on Base Sepolia and one on local EVMs."
    },
    {
      "name": "SUCCESSION_MARKETPLACE",
      "help": "Which marketplace to publish to and read from. Defaults to http://127.0.0.1:8000, which is right for local development and wrong for everything else."
    },
    {
      "name": "BASE_SEPOLIA_RPC_URL",
      "help": "How to reach the chain."
    },
    {
      "name": "SUCCESSION_DEPLOYMENT",
      "help": "Path to the deployment record. The packaged copy is used when this is unset and no checkout is present."
    },
    {
      "name": "SUCCESSION_ARTIFACTS",
      "help": "Path to the contract ABI. Same fallback as the deployment record."
    },
    {
      "name": "SUCCESSION_VAULT",
      "help": "Where the seller's listings, envelopes and content keys are kept. Defaults to ~/.succession/listings."
    },
    {
      "name": "SUCCESSION_MCP_ALLOW_WRITES",
      "help": "Set to 1 to let an MCP client call the tools that spend money, release a decryption key, or permanently seal an agent. Off by default because sealing has no undo."
    },
    {
      "name": "SIBYL_CREDENTIALS",
      "help": "Path to credentials.json. Without it the memory SDK enforces a strict 5 MB cap and the paid features gate off."
    }
  ],
  "groups": [
    {
      "title": "Start here",
      "note": "Nothing here changes anything.",
      "commands": [
        "status",
        "audit",
        "market",
        "show"
      ]
    },
    {
      "title": "Selling",
      "note": "Runs on your own machine, against your own store.",
      "commands": [
        "inventory",
        "value",
        "preview",
        "prove",
        "export",
        "list",
        "publish",
        "fulfil",
        "listings"
      ]
    },
    {
      "title": "Buying",
      "note": "Fund escrow, then claim after independent evaluator settlement.",
      "commands": [
        "buy",
        "claim"
      ]
    },
    {
      "title": "Evaluating",
      "note": "Import into an isolated tenant, verify, and settle on the evaluator's signed verdict.",
      "commands": [
        "evaluate"
      ]
    },
    {
      "title": "Compatibility",
      "note": "Retained to explain the evaluator migration to older buyer scripts.",
      "commands": [
        "confirm"
      ]
    },
    {
      "title": "Working with a package directly",
      "note": "For inspecting a file you were handed.",
      "commands": [
        "inspect",
        "verify",
        "import"
      ]
    }
  ]
};
