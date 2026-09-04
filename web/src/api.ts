/**
 * The service client. Every shape here mirrors what the Python returns —
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

export interface Preview {
  agent_identity: string;
  tenure_days: number;
  counts: Record<string, number>;
  memory_size_bytes: number;
  category_breakdown: Record<string, number>;
  public_counterparties: string[];
  withheld_non_transferable: number;
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

export const api = {
  reset: (categories?: string[]) =>
    request<{ listing_id: string; committed_root: string }>("/api/demo/reset", {
      method: "POST",
      body: JSON.stringify({ categories: categories ?? null }),
    }),
  listing: () => request<Listing>("/api/listing"),
  preview: () => request<Preview>("/api/listing/preview"),
  buy: () => request<Listing>("/api/listing/buy", { method: "POST", body: "{}" }),
  transfer: () => request<Outcome>("/api/listing/transfer", { method: "POST" }),
  seal: (tenant: string) =>
    request<{ sealed: boolean; record: { sealed_at: string; reason: string } | null }>(
      `/api/seal/${tenant}`,
    ),
  writeAttempt: () =>
    request<{ accepted: boolean; reason: string }>("/api/seller/write-attempt", {
      method: "POST",
      body: "{}",
    }),
  message: (side: "seller" | "buyer", message: string) =>
    request<Reply>(`/api/agent/${side}/message`, {
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

export function abbreviate(value: string, head = 10, tail = 8): string {
  if (!value) return "—";
  return value.length <= head + tail + 1
    ? value
    : `${value.slice(0, head)}…${value.slice(-tail)}`;
}
