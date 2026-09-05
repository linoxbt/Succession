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
  factors: {
    name: string;
    value: string;
    weight: string;
    contribution: string;
    explanation: string;
  }[];
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
    request<{ listings: MarketRow[]; count: number; chain: boolean }>(
      "/api/marketplace",
    ),
  listing: (id: string) => request<MarketRow>(`/api/listing/${id}`),
  /** Ciphertext. Public on purpose, inert without the content key. */
  envelope: (id: string) => request<unknown>(`/api/listing/${id}/envelope`),
  chain: () => request<ChainStatus>("/api/chain"),
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

