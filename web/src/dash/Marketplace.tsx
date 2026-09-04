/**
 * The marketplace: every listed memory asset, and what it is worth.
 *
 * Every figure on this screen is computed by the pipeline from a real export of
 * a real store — the root, the record count, the memory size, the valuation.
 * None of it is written down. That is the difference between a marketplace and
 * a mock-up, and it is why the table shows six listings rather than sixty.
 *
 * The KPI row leads with one hero figure and supports it with tiles; the table
 * is sortable and filterable; selecting a row opens the listing's valuation
 * derivation, because "why is this priced at that" is the question a buyer
 * actually has.
 */
import { useMemo, useState } from "react";
import type { MarketRow } from "../api";
import { formatAmount } from "../api";
import { Badge, Empty, Field, Hash, Panel, Rule, Table, Td, type Tone } from "../ui";
import { Distribution, FactorBars, Hero, Tile, compact } from "../ui/charts";

type SortKey = "value" | "price" | "spread" | "records" | "tenure" | "name";

const STATE_TONE: Record<string, Tone> = {
  open: "neutral",
  escrowed: "accent",
  confirmed: "good",
  refunded: "bad",
};

const STATE_LABEL: Record<string, string> = {
  open: "Listed",
  escrowed: "In escrow",
  confirmed: "Settled",
  refunded: "Refunded",
};

export function Marketplace({
  rows,
  onOpenListing,
}: {
  rows: MarketRow[];
  onOpenListing: (listingId: string) => void;
}) {
  const [sort, setSort] = useState<SortKey>("value");
  const [vertical, setVertical] = useState<string>("all");
  const [state, setState] = useState<string>("all");
  const [selected, setSelected] = useState<string | null>(null);

  const verticals = useMemo(
    () => Array.from(new Set(rows.map((r) => r.vertical))).sort(),
    [rows],
  );

  const filtered = useMemo(() => {
    const value = (r: MarketRow) => Number(r.preview.valuation?.amount ?? 0);
    return rows
      .filter((r) => vertical === "all" || r.vertical === vertical)
      .filter((r) => state === "all" || r.listing.state === state)
      .sort((a, b) => {
        const spread = (r: MarketRow) => {
          const v = Number(r.preview.valuation?.amount ?? 0);
          return v ? (r.listing.price / 1_000_000 - v) / v : 0;
        };
        switch (sort) {
          case "spread":
            return spread(a) - spread(b);
          case "price":
            return b.listing.price - a.listing.price;
          case "records":
            return (b.preview.counts.total_records ?? 0) - (a.preview.counts.total_records ?? 0);
          case "tenure":
            return b.preview.tenure_days - a.preview.tenure_days;
          case "name":
            return a.name.localeCompare(b.name);
          default:
            return value(b) - value(a);
        }
      });
  }, [rows, sort, vertical, state]);

  if (!rows.length) {
    return (
      <Panel title="Marketplace">
        <Empty>No listings. Post one from the Listing tab.</Empty>
      </Panel>
    );
  }

  const totalValue = rows.reduce(
    (sum, r) => sum + Number(r.preview.valuation?.amount ?? 0),
    0,
  );
  const totalRecords = rows.reduce((s, r) => s + (r.preview.counts.total_records ?? 0), 0);
  const totalEvents = rows.reduce((s, r) => s + (r.preview.counts.journal_events ?? 0), 0);
  const withAcp = rows.filter((r) => r.preview.acp?.registered).length;
  const settled = rows.filter((r) => r.listing.state === "confirmed").length;
  const medianTenure = median(rows.map((r) => r.preview.tenure_days));

  const detail = filtered.find((r) => r.listing.listing_id === selected) ?? null;

  return (
    <div className="space-y-6">
      {/* KPI row — one hero, then supporting tiles. */}
      <Panel>
        <div className="grid divide-y divide-line lg:grid-cols-[1.4fr_2.6fr] lg:divide-x lg:divide-y-0">
          <Hero
            label="Memory value listed"
            value={compact(totalValue, "$")}
            sub={`${rows.length} listings · reference valuations, not enforced by the contract`}
          />
          <div className="grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-4 sm:divide-y-0">
            <Tile label="Records for sale" value={compact(totalRecords)} sub="across all tiers" />
            <Tile label="Journal events" value={compact(totalEvents)} sub="settled history" />
            <Tile
              label="Verifiable earnings"
              value={`${withAcp}/${rows.length}`}
              sub={withAcp ? "ACP-registered" : "none registered yet"}
            />
            <Tile label="Median tenure" value={`${medianTenure}d`} sub="since first event" />
          </div>
        </div>
      </Panel>

      {/* Filters, in one row above the table. */}
      <Panel
        title="Listings"
        action={
          <span className="text-xs text-faint tnum">
            {filtered.length} of {rows.length}
            {settled ? ` · ${settled} settled` : ""}
          </span>
        }
      >
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-3">
          <Select label="Vertical" value={vertical} onChange={setVertical}
            options={[["all", "All verticals"], ...verticals.map((v) => [v, v] as [string, string])]} />
          <Select label="State" value={state} onChange={setState}
            options={[["all", "Any state"], ["open", "Listed"], ["escrowed", "In escrow"], ["confirmed", "Settled"], ["refunded", "Refunded"]]} />
          <Select label="Sort" value={sort} onChange={(v) => setSort(v as SortKey)}
            options={[["value", "Valuation"], ["price", "Asking price"], ["spread", "Best spread"], ["records", "Records"], ["tenure", "Tenure"], ["name", "Name"]]} />
        </div>

        <Table head={["Agent", "Vertical", "Tenure", "Records", "ACP", "Valuation", "Ask", "Spread", "State", ""]}>
          {filtered.map((r) => {
            const isOpen = selected === r.listing.listing_id;
            return (
              <tr
                key={r.listing.listing_id}
                onClick={() => setSelected(isOpen ? null : r.listing.listing_id)}
                className={`cursor-pointer transition-colors ${isOpen ? "bg-raised/60" : "hover:bg-raised/40"}`}
              >
                <Td>
                  <span className="flex items-center gap-2">
                    <span className="font-medium text-primary">{r.name}</span>
                    {r.featured ? <Badge tone="accent">Featured</Badge> : null}
                  </span>
                  <span className="mt-0.5 block font-mono text-[0.6875rem] text-faint">
                    {r.listing.agent_id}
                  </span>
                </Td>
                <Td className="text-secondary">{r.vertical}</Td>
                <Td className="tnum text-secondary">{r.preview.tenure_days}d</Td>
                <Td className="tnum">{r.preview.counts.total_records}</Td>
                <Td>
                  {r.preview.acp?.registered ? (
                    <span className="tnum text-good">{r.preview.acp.completed_jobs}</span>
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                </Td>
                <Td className="tnum font-medium">${r.preview.valuation?.amount ?? "—"}</Td>
                <Td className="tnum text-secondary">
                  {formatAmount(r.listing.price, r.listing.currency)}
                </Td>
                <Td>
                  <Spread row={r} />
                </Td>
                <Td>
                  <Badge tone={STATE_TONE[r.listing.state] ?? "neutral"}>
                    {STATE_LABEL[r.listing.state] ?? r.listing.state}
                  </Badge>
                </Td>
                <Td className="text-right text-faint">{isOpen ? "−" : "+"}</Td>
              </tr>
            );
          })}
        </Table>
        {filtered.length === 0 ? <Empty>No listing matches those filters.</Empty> : null}
      </Panel>

      {detail ? <Detail row={detail} onOpen={() => onOpenListing(detail.listing.listing_id)} /> : null}

      <Panel title="Records by category" action={<span className="text-xs text-faint">Across every listing</span>}>
        <Distribution data={categoryTotals(rows)} total={totalRecords} />
      </Panel>
    </div>
  );
}

/**
 * What the seller asks against their own reference valuation.
 *
 * A real marketplace signal, and the reason the price is derived from the
 * valuation rather than typed: a seller asking 18% over is saying something,
 * and a seller asking under is saying something else. Sign is not enough on
 * its own, so the number is always shown with it.
 */
function Spread({ row }: { row: MarketRow }) {
  const valuation = Number(row.preview.valuation?.amount ?? 0);
  if (!valuation) return <span className="text-faint">—</span>;
  const ask = row.listing.price / 1_000_000;
  const pct = Math.round(((ask - valuation) / valuation) * 100);
  if (pct === 0) return <span className="tnum text-faint">at value</span>;
  return (
    <span className={`tnum ${pct > 0 ? "text-warn" : "text-good"}`}>
      {pct > 0 ? "+" : ""}
      {pct}%
    </span>
  );
}

function Detail({ row, onOpen }: { row: MarketRow; onOpen: () => void }) {
  const v = row.preview.valuation;
  return (
    <Panel
      title={`${row.name} — valuation`}
      action={
        <button onClick={onOpen} className="text-[0.8125rem] text-accent hover:underline">
          Open listing →
        </button>
      }
    >
      {v ? (
        <>
          <FactorBars
            reference={1}
            data={v.factors.map((f) => ({
              label: f.name,
              value: Number(f.value),
              note: f.explanation,
            }))}
          />
          <Rule />
          <p className="px-5 py-3 font-mono text-xs text-faint">
            ${v.base_price} base × five factors = ${v.amount}
          </p>
        </>
      ) : null}
      <Rule />
      <dl>
        <Field label="Committed hash">
          <Hash value={row.listing.hash_commitment} chars={12} />
        </Field>
        <Field label="Categories">{row.listing.categories.join(", ")}</Field>
        <Field label="Memory size">{(row.preview.memory_size_bytes / 1024).toFixed(1)} KB</Field>
        <Field label="Counterparties">{row.preview.category_breakdown.relationship ?? 0}</Field>
        <Field label="Withheld">
          {row.preview.withheld_non_transferable} non-transferable, excluded before hashing
        </Field>
      </dl>
    </Panel>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-faint">
      <span className="sr-only sm:not-sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-line bg-panel px-2.5 py-1.5 text-[0.8125rem] text-primary"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid]! : Math.round((sorted[mid - 1]! + sorted[mid]!) / 2);
}

function categoryTotals(rows: MarketRow[]): { label: string; value: number }[] {
  const totals = new Map<string, number>();
  for (const row of rows) {
    for (const [category, count] of Object.entries(row.preview.category_breakdown)) {
      totals.set(category, (totals.get(category) ?? 0) + count);
    }
    totals.set("journal", (totals.get("journal") ?? 0) + (row.preview.counts.journal_events ?? 0));
  }
  return [...totals.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}
