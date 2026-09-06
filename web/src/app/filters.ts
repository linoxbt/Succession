/**
 * Marketplace filtering and search.
 *
 * Kept out of the view so the rules can be read, and tested, without a browser.
 * Every filter corresponds to something the protocol actually measures. There
 * is no relevance score and no popularity ordering, because neither exists in
 * the data and inventing one would be the first fabricated metric on a screen
 * whose whole argument is that its figures trace to something.
 *
 * Filter state lives in the query string, so a filtered market is a link.
 */
import type { MarketRow, Preview } from "../api";
import { SELLABLE_DIRECTORIES } from "./domain";

export type ScopeFilter = "any" | "full" | "partial";
export type VerifiedFilter = "any" | "verified" | "unverified";
export type AgeFilter = "any" | "under3" | "3to6" | "6to12" | "over12";
export type BandFilter = "any" | "low" | "medium" | "high";
export type StateFilter = "any" | "open" | "escrowed" | "confirmed" | "refunded";
export type SortKey = "price-desc" | "price-asc" | "records-desc" | "age-desc";

export interface Filters {
  q: string;
  scope: ScopeFilter;
  verified: VerifiedFilter;
  age: AgeFilter;
  density: BandFilter;
  breadth: BandFilter;
  performance: BandFilter;
  state: StateFilter;
  sort: SortKey;
}

export const EMPTY: Filters = {
  q: "",
  scope: "any",
  verified: "any",
  age: "any",
  density: "any",
  breadth: "any",
  performance: "any",
  state: "any",
  sort: "price-desc",
};

export function fromQuery(params: URLSearchParams): Filters {
  const read = <T extends string>(key: keyof Filters, fallback: T): T =>
    (params.get(key) as T | null) ?? fallback;

  return {
    q: params.get("q") ?? "",
    scope: read("scope", EMPTY.scope),
    verified: read("verified", EMPTY.verified),
    age: read("age", EMPTY.age),
    density: read("density", EMPTY.density),
    breadth: read("breadth", EMPTY.breadth),
    performance: read("performance", EMPTY.performance),
    state: read("state", EMPTY.state),
    sort: read("sort", EMPTY.sort),
  };
}

/** Only non-default values are written, so a pristine market has a clean URL. */
export function toQuery(filters: Filters): Record<string, string | null> {
  const patch: Record<string, string | null> = {};
  for (const key of Object.keys(EMPTY) as (keyof Filters)[]) {
    patch[key] = filters[key] === EMPTY[key] ? null : String(filters[key]);
  }
  return patch;
}

export function activeCount(filters: Filters): number {
  return (Object.keys(EMPTY) as (keyof Filters)[]).filter(
    (key) => key !== "sort" && filters[key] !== EMPTY[key],
  ).length;
}

// --- the measurements a filter reads -------------------------------------

interface Measured {
  described: boolean;
  records: number;
  tenureDays: number;
  counterparties: number;
  eventsPerDay: number;
  successRate: number | null;
  offered: number;
  verified: boolean;
}

export function measure(row: MarketRow): Measured {
  const preview = row.preview as Preview | undefined;
  const inventory = preview?.inventory ?? {};
  const tenureDays = preview?.tenure_days ?? 0;
  const events = inventory.history?.sellable ?? 0;

  return {
    described: Boolean(preview?.agent_identity),
    records: Object.values(inventory).reduce((sum, e) => sum + e.sellable, 0),
    tenureDays,
    counterparties: inventory.relationships?.sellable ?? 0,
    eventsPerDay: tenureDays > 0 ? events / tenureDays : 0,
    successRate: preview?.acp?.success_rate ? Number(preview.acp.success_rate) : null,
    offered: SELLABLE_DIRECTORIES.filter((d) => inventory[d]?.offerable).length,
    verified: Boolean(row.integrity?.root),
  };
}

/**
 * Band thresholds. Absolute rather than relative to the current result set: a
 * listing must not change from "high" to "low" because another listing was
 * filtered out, which is what percentile bands would do.
 */
function band(value: number, medium: number, high: number): BandFilter {
  if (value >= high) return "high";
  if (value >= medium) return "medium";
  return "low";
}

function matches(row: MarketRow, filters: Filters): boolean {
  const m = measure(row);

  if (filters.state !== "any" && row.listing.state !== filters.state) return false;

  if (filters.verified !== "any") {
    if (filters.verified === "verified" && !m.verified) return false;
    if (filters.verified === "unverified" && m.verified) return false;
  }

  if (filters.scope !== "any") {
    // An undescribed listing has no declared scope, so it cannot satisfy a
    // scope filter either way. Excluding it is honest; guessing "full" is not.
    if (!m.described) return false;
    const full = m.offered === SELLABLE_DIRECTORIES.length;
    if (filters.scope === "full" && !full) return false;
    if (filters.scope === "partial" && full) return false;
  }

  if (filters.age !== "any") {
    if (!m.described) return false;
    const months = m.tenureDays / 30;
    const ok =
      filters.age === "under3"
        ? months < 3
        : filters.age === "3to6"
          ? months >= 3 && months < 6
          : filters.age === "6to12"
            ? months >= 6 && months < 12
            : months >= 12;
    if (!ok) return false;
  }

  if (filters.density !== "any") {
    if (!m.described) return false;
    if (band(m.eventsPerDay, 0.25, 2) !== filters.density) return false;
  }

  if (filters.breadth !== "any") {
    if (!m.described) return false;
    if (band(m.counterparties, 25, 150) !== filters.breadth) return false;
  }

  if (filters.performance !== "any") {
    // A rate is withheld below five resolved outcomes, and a listing that
    // declines to claim one must not be filtered as though it scored zero.
    if (m.successRate === null) return false;
    if (band(m.successRate, 0.75, 0.9) !== filters.performance) return false;
  }

  if (filters.q.trim()) {
    const needle = filters.q.trim().toLowerCase();
    const haystack = [
      row.name,
      row.vertical,
      row.agent_identity,
      row.listing.listing_id,
      row.listing.agent_id,
      row.listing.seller,
      row.listing.buyer,
      row.listing.hash_commitment,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (!haystack.includes(needle)) return false;
  }

  return true;
}

const SORTS: Record<SortKey, (a: MarketRow, b: MarketRow) => number> = {
  "price-desc": (a, b) => b.listing.price - a.listing.price,
  "price-asc": (a, b) => a.listing.price - b.listing.price,
  "records-desc": (a, b) => measure(b).records - measure(a).records,
  "age-desc": (a, b) => measure(b).tenureDays - measure(a).tenureDays,
};

export function apply(rows: MarketRow[], filters: Filters): MarketRow[] {
  return rows.filter((row) => matches(row, filters)).sort(SORTS[filters.sort]);
}
