/**
 * The service client. Every shape here mirrors what the Python returns,
 * nothing is computed on this side, because a number the UI derives is a number
 * that can disagree with the one the contract enforces.
 */

export type ListingState = "open" | "escrowed" | "confirmed" | "refunded";

export interface Listing {
  listing_id: string;
  agent_id: string;
  seller: string;
  seller_signature: string;
  hash_commitment: string;
  price: number;
  currency: string;
  categories: string[];
  valuation_reference: string;
  state: ListingState;
  buyer: string;
  escrow_balance: number;
  delivered_hash: string;
  sealed: boolean;
  created_at: string;
  settled_at: string;
}

export interface ValuationFactor {
  name: string;
  value: string;
  inputs: Record<string, unknown>;
  explanation: string;
}

export interface AcpHistory {
  agent_address: string;
  agent_id: number | null;
  agent_name: string;
  registered: boolean;
  source: "live" | "memory" | "recorded";
  fetched_at: string;
  completed_jobs: number;
  failed_jobs: number;
  gross_volume: string;
  distinct_counterparties: number;
  success_rate: string | null;
  verifiable_job_ids: number[];
  verification: string;
}

export interface Overview {
  chain: boolean;
  explanation: string;
  totals: {
    listings?: number;
    by_state?: Record<string, number>;
    volume_settled?: number;
    volume_open?: number;
    agents?: number;
    sellers?: number;
    with_data_room?: number;
  };
  listings: MarketRow[];
  /** Demonstration rows, kept out of `listings` and out of `totals`. */
  demo_listings?: MarketRow[];
  deployment: ChainStatus["deployment"];
  capabilities: Capability[];
  reputation_model: ReputationModel;
}

/** One SMP directory, and how much of it the market currently offers. */
export interface Capability {
  category: string;
  transferable: boolean;
  status: "live" | "coming-soon";
  note: string;
  records_sellable: number;
  records_withheld: number;
  listings: number;
}

/** The weights the portable score is built from, published rather than hidden. */
export interface ReputationModel {
  basis: string;
  factors: { name: string; weight: string; note: string }[];
  grades: string[];
  does_not_transfer: { item: string; why: string }[];
}

/** One contract event: what happened, when, and in which transaction. */
export interface ActivityEvent {
  event:
    | "Listed"
    | "Escrowed"
    | "TransferConfirmed"
    | "Refunded"
    | "Cancelled"
    | "AgentSealed";
  /** Empty for AgentSealed, which is keyed by agent rather than by listing. */
  listing_id: string;
  block: number;
  timestamp: number | null;
  tx: string;
  args: Record<string, string | number | boolean>;
}

export interface Activity {
  chain: boolean;
  explanation: string;
  events: ActivityEvent[];
  count: number;
  explorer?: string;
}

export interface AgentHolding {
  agent_id: number;
  identity: string;
}

export interface AgentsHeld {
  owner: string;
  agents: AgentHolding[];
  /** Ground truth from balanceOf. */
  balance: number;
  found: number;
  /** False means "there are more, scan deeper", not "this wallet holds none". */
  complete: boolean;
  scanned_from_block: number;
  head_block: number;
}

export interface Reputation {
  score: string;
  grade: string;
  links: number;
  basis: string;
  /** When the score was derived. It is recomputed per read, never stored, so
   *  this is the age of the answer rather than the age of a record. */
  computed_at?: string;
  factors: {
    name: string;
    value: string;
    weight: string;
    contribution: string;
    /** The raw and intermediate numbers the factor was computed from, so the
     *  score can be re-derived by hand rather than taken on faith. */
    inputs?: Record<string, unknown>;
    explanation: string;
  }[];
}

/** One SMP directory as the seller's own store reports it.
 *
 *  The two withheld counts are not interchangeable. `withheld_by_seller` is a
 *  choice and could be reversed by listing again; `withheld_without_consent` is
 *  a record a counterparty never agreed to move, and no price changes it. */
export interface CategoryInventory {
  category: string;
  sellable: number;
  withheld_by_seller: number;
  withheld_without_consent: number;
  total: number;
  depth: "empty" | "thin" | "moderate" | "deep";
  offerable: boolean;
  newest: string;
  oldest: string;
}

/** The two-level Merkle manifest: one subroot per directory, one global root. */
export interface IntegrityManifest {
  algorithm?: string;
  construction?: string;
  root?: string;
  leaf_count?: number;
  categories?: { category: string; subroot: string; leaf_count: number }[];
}

/** The signed provenance header, and the chain of owners inside it. */
export interface ProvenanceHeader {
  smp_version?: string;
  agent_identity?: string;
  created_at?: string;
  memory_version?: number;
  categories?: string[];
  provenance_chain?: {
    owner: string;
    acquired_at: string;
    verified_hash: string;
    memory_version?: number;
  }[];
  integrity_root?: string;
  permissions_hash?: string;
  signature?: string | null;
}

export interface Preview {
  reputation?: Reputation | null;
  agent_identity: string;
  tenure_days: number;
  counts: Record<string, number>;
  memory_size_bytes: number;
  category_breakdown: Record<string, number>;
  public_counterparties: string[];
  withheld_non_transferable: number;
  /** Per SMP directory: how much is for sale, and how much the seller withheld.
   *  A directory with `sellable: 0` cannot form part of any transfer, which is
   *  what the scope selector greys out. */
  category_transferability?: Record<string, { sellable: number; withheld: number }>;
  /** Per directory, with the two withheld reasons kept apart. Served by the
   *  data room since it existed; it simply had no type here before. */
  inventory?: Record<string, CategoryInventory>;
  disclosure: string;
  committed_root?: string;
  acp: AcpHistory | null;
  provenance_of_figures: {
    self_reported: string[];
    independently_verifiable: string[];
  };
  valuation?: {
    currency: string;
    base_price: string;
    amount: string;
    formula: string;
    factors: ValuationFactor[];
    excluded: Record<string, string>;
  };
}

export interface Certificate {
  memory_asset: string;
  origin_agent: string;
  successor_agent: string;
  memory_version: number;
  records_transferred: number;
  integrity_hash: string;
  categories_transferred: string[];
  seller_signature: string;
  seller_tenant_sealed_at: string;
  settlement_reference: string;
  transfer_date: string;
  transfer_status: string;
}

export interface Outcome {
  listing_id: string;
  outcome: "verified" | "refunded";
  committed_root: string;
  delivered_root: string;
  failure_reason: string;
  receipt: {
    outcome: string;
    amount: number;
    paid_to: string;
    identity_transferred_to: string;
    reference: string;
    settled_at: string;
    /** "buyer" or "arbiter". A buyer vouching for their own delivery and a
     *  disinterested evaluator that re-derived it are not the same evidence. */
    confirmed_by?: string;
  } | null;
  certificate: Certificate | null;
  certificate_text?: string;
  seal: { tenant_id: string; sealed_at: string; reason: string } | null;
}

export interface Reply {
  text: string;
  recalled: boolean;
  citations: { tier: string; key: string }[];
}

export interface MarketRow {
  listing: Listing;
  preview: Preview;
  name: string;
  vertical: string;
  valuation: string;
  agent_identity: string;
  has_envelope?: boolean;
  /** False when the seller published nothing beyond the on-chain listing. */
  has_metadata?: boolean;
  /** Published alongside the data room. Empty when the seller listed before
   *  these were part of the format, which the UI reports rather than hides. */
  integrity?: IntegrityManifest;
  provenance?: ProvenanceHeader;
  /** True only for the demonstration listings. The service keeps them in their
   *  own field so no total can count them; this flag survives the point where
   *  a screen concatenates the two lists for display. */
  demo?: boolean;
  /** What a demo row says about itself on screen. */
  notice?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* the status line is the best we have */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

/**
 * Two clients, deliberately not one.
 *
 * `market` reads listings that exist because someone paid gas to commit their
 * root; the contract is the source of truth and this service only adds what the
 * contract has no field for. `walkthrough` drives a scripted sale on a sample
 * agent, which settles through an in-process mirror and touches no chain.
 *
 * They are separate objects so the boundary is legible at the call site rather
 * than buried in a URL. Every walkthrough response also carries `simulated`,
 * so a screen keys its banner off the payload and cannot render one as the
 * other by forgetting which client it used.
 */
// One definition, kept beside the wallet code that consumes it most. Imported
// as well as re-exported because `market.chain()` names it in its own return
// type, and a bare re-export does not bring it into local scope.
import type { ChainStatus } from "./chain/Wallet";
export type { ChainStatus };

export const market = {
  listings: () =>
    request<{
      listings: MarketRow[];
      count: number;
      chain: boolean;
      demo_listings?: MarketRow[];
    }>("/api/marketplace"),
  listing: (id: string) => request<MarketRow>(`/api/listing/${id}`),
  /** Ciphertext. Public on purpose, inert without the content key. */
  envelope: (id: string) => request<unknown>(`/api/listing/${id}/envelope`),
  chain: () => request<ChainStatus>("/api/chain"),
  /** Everything the service knows, in one read. */
  overview: () => request<Overview>("/api/overview"),
  /** The event ledger: what happened, rather than what is true now. */
  activity: (limit = 100) =>
    request<Activity>(`/api/activity?limit=${limit}`),
  /** Which ERC-8004 agents a wallet holds, for choosing a successor. */
  agents: (owner: string) => request<AgentsHeld>(`/api/agents/${owner}`),
};

export interface Simulated {
  simulated: true;
  notice: string;
}

export const walkthrough = {
  reset: (categories?: string[]) =>
    request<{ listing_id: string; committed_root: string; price: number } & Simulated>(
      "/api/walkthrough/reset",
      { method: "POST", body: JSON.stringify({ categories: categories ?? null }) },
    ),
  listing: () => request<Listing & Simulated>("/api/walkthrough/listing"),
  preview: () => request<Preview & Simulated>("/api/walkthrough/preview"),
  buy: () => request<Listing & Simulated>("/api/walkthrough/buy", { method: "POST" }),
  transfer: () =>
    request<Outcome & Simulated>("/api/walkthrough/transfer", { method: "POST" }),
  outcome: () => request<Outcome & Simulated>("/api/walkthrough/outcome"),
  seal: (tenant: string) =>
    request<
      {
        sealed: boolean;
        record: { sealed_at: string; reason: string } | null;
      } & Simulated
    >(`/api/walkthrough/seal/${tenant}`),
  writeAttempt: () =>
    request<{ accepted: boolean; reason: string } & Simulated>(
      "/api/walkthrough/write-attempt",
      { method: "POST", body: "{}" },
    ),
  message: (side: "seller" | "buyer", message: string) =>
    request<Reply & Simulated>(`/api/walkthrough/agent/${side}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};


/** Money arrives in minor units; render it the way a closing statement would. */
export function formatAmount(minorUnits: number, currency: string): string {
  return `${(minorUnits / 1_000_000).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${currency}`;
}

