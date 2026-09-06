/**
 * The seam between the interface and whatever is behind it.
 *
 * Views call `useService()` and never `fetch`. That is what lets a screen be
 * built against a shape the backend does not serve yet, and lets the same
 * screen switch to the real thing without an edit.
 *
 * Two implementations. `HttpService` is the real one and wraps the endpoints in
 * `api.ts`. `MockService` answers from fixtures and makes no network call at
 * all, for working offline or on a screen whose route is still being written.
 *
 * The mock is development-only and says so on every row it returns: its
 * listings carry `demo: true`, exactly like the service's own demonstration
 * rows, so a fixture that somehow reached a real screen would be stamped rather
 * than mistaken for a sale. It is selected by `VITE_SERVICE=mock` at build
 * time, so a production bundle does not contain a path that reaches it.
 */
import {
  market,
  type AgentsHeld,
  type ChainStatus,
  type MarketRow,
  type Overview,
} from "../api";

/** Listings, with the two collections kept apart as the service returns them. */
export interface Listings {
  /** Real listings, read from the contract. Every figure derives from these. */
  real: MarketRow[];
  /** Demonstration rows. Never counted, never purchasable. */
  demo: MarketRow[];
  /** Whether a contract is deployed and reachable. */
  chain: boolean;
}

export interface SuccessionService {
  readonly kind: "http" | "mock";
  overview(): Promise<Overview>;
  listings(): Promise<Listings>;
  listing(id: string): Promise<MarketRow>;
  agents(owner: string): Promise<AgentsHeld>;
  chain(): Promise<ChainStatus>;
}

export const HttpService: SuccessionService = {
  kind: "http",

  overview: () => market.overview(),

  listings: async () => {
    const body = await market.listings();
    return {
      real: body.listings,
      demo: body.demo_listings ?? [],
      chain: body.chain,
    };
  },

  listing: (id) => market.listing(id),
  agents: (owner) => market.agents(owner),
  chain: () => market.chain(),
};

// --- the mock ------------------------------------------------------------

function fixtureRow(): MarketRow {
  const inventory = {
    identity: {
      category: "identity",
      sellable: 3,
      withheld_by_seller: 0,
      withheld_without_consent: 0,
      total: 3,
      depth: "thin" as const,
      offerable: true,
      newest: "",
      oldest: "",
    },
    relationships: {
      category: "relationships",
      sellable: 64,
      withheld_by_seller: 2,
      withheld_without_consent: 9,
      total: 75,
      depth: "deep" as const,
      offerable: true,
      newest: "",
      oldest: "",
    },
  };

  return {
    listing: {
      listing_id: "mock-0001",
      agent_id: "9900",
      seller: "0x0000000000000000000000000000000000000000",
      seller_signature: "",
      hash_commitment: "0x" + "ab".repeat(32),
      price: 5_000_000,
      currency: "USDC",
      categories: ["identity", "relationships"],
      valuation_reference: "5000.00",
      state: "open",
      buyer: "",
      escrow_balance: 0,
      delivered_hash: "",
      sealed: false,
      created_at: "",
      settled_at: "",
    },
    preview: {
      agent_identity: "erc8004:84532:9900",
      tenure_days: 120,
      counts: { total_records: 78 },
      memory_size_bytes: 91_000,
      category_breakdown: {},
      public_counterparties: [],
      withheld_non_transferable: 9,
      category_transferability: {
        identity: { sellable: 3, withheld: 0 },
        relationships: { sellable: 64, withheld: 11 },
      },
      inventory,
      disclosure: "Aggregate statistics only.",
      acp: null,
      provenance_of_figures: { self_reported: ["counts"], independently_verifiable: [] },
    },
    name: "Fixture Agent",
    vertical: "Development fixture",
    valuation: "5000.00",
    agent_identity: "erc8004:84532:9900",
    has_envelope: false,
    has_metadata: true,
    demo: true,
    notice: "Local development fixture. Not a listing.",
  };
}

export const MockService: SuccessionService = {
  kind: "mock",

  overview: async () => ({
    chain: false,
    explanation: "Local fixtures. No contract is being read.",
    totals: {},
    listings: [],
    demo_listings: [fixtureRow()],
    deployment: null,
    capabilities: [],
    reputation_model: {
      basis: "Fixture.",
      factors: [],
      grades: [],
      does_not_transfer: [],
    },
  }),

  listings: async () => ({ real: [], demo: [fixtureRow()], chain: false }),

  listing: async (id) => {
    const row = fixtureRow();
    row.listing.listing_id = id;
    return row;
  },

  agents: async (owner) => ({
    owner,
    agents: [],
    balance: 0,
    found: 0,
    complete: true,
    scanned_from_block: 0,
    head_block: 0,
  }),

  chain: async () => ({
    mode: "none",
    explanation: "Local fixtures. No contract is being read.",
    chain_id: null,
    deployment: null,
  }),
};

/**
 * Which implementation this build uses. Read from the environment rather than
 * from a runtime toggle, so a production bundle cannot be switched into
 * fixtures by anything a page can set.
 */
export const service: SuccessionService =
  import.meta.env.VITE_SERVICE === "mock" ? MockService : HttpService;
