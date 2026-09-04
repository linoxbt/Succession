/**
 * The marketplace: every listed memory asset, and what it is worth.
 *
 * Every figure on this screen is computed by the pipeline from a real export of
 * a real store — the root, the record count, the memory size, the valuation.
 * None of it is written down. That is the difference between a marketplace and
 * a mock-up, and it is why the table shows six listings rather than sixty.
 *
 * The register is the same data room as every other screen: a summary as a
 * definition list, then a sortable, filterable table, then the selected
 * listing's valuation derivation — because "why is this priced at that" is the
 * question a buyer actually has.
 *
 * The stat tiles and bar charts that used to head this view are gone. A grid of
 * tiles is the product-card idiom under another name, and it flattens six
 * figures into six equally important boxes; a definition list lets a reader see
 * which number is load-bearing. The valuation factors read better as the same
 * table the listing screen already uses, so they use it.
 */
import { useMemo, useState } from "react";
import type { MarketRow } from "../api";
import { formatAmount } from "../api";
import {
  Badge,
  Empty,
  Field,
  FieldList,
  Hash,
  Section,
  Table,
  Td,
  type Tone,
} from "../ui";

type SortKey = "value" | "price" | "spread" | "records" | "tenure" | "name";

const STATE_TONE: Record<string, Tone> = {
  open: "neutral",
  escrowed: "escrow",
  confirmed: "closed",
  refunded: "void",
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
      <Section title="Marketplace">
        <Empty>No listings. Post one from the Listing tab.</Empty>
      </Section>
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
    <div className="space-y-10">
      <Section title="Memory listed">
        <FieldList className="mt-4">
          <Field label="Total reference valuation" emphasis>
            ${totalValue.toLocaleString("en-US")}
          </Field>
          <Field label="Listings">
            <span className="tnum">{rows.length}</span>
            <span className="text-muted">
              {" "}
              — reference valuations, not enforced by the contract
            </span>
          </Field>
          <Field label="Records for sale">
            <span className="tnum">{totalRecords.toLocaleString("en-US")}</span>
            <span className="text-muted"> across all tiers</span>
          </Field>
          <Field label="Journal events">
            <span className="tnum">{totalEvents.toLocaleString("en-US")}</span>
            <span className="text-muted"> of settled history</span>
          </Field>
          <Field label="Verifiable earnings">
            <span className="tnum">
              {withAcp}/{rows.length}
            </span>
            <span className="text-muted">
              {withAcp ? " ACP-registered" : " — none registered yet"}
            </span>
          </Field>
          <Field label="Median tenure">
            <span className="tnum">{medianTenure}</span> days since first event
          </Field>
          <Field label="Records by category">
            <span className="text-muted">
              {categoryTotals(rows)
                .map((c) => `${c.label} ${c.value}`)
                .join(" · ")}
            </span>
          </Field>
        </FieldList>
      </Section>

      {/* Filters, in one row above the table. */}
      <Section
        title="Listings"
        action={
          <span className="text-[0.8125rem] text-muted tnum">
            {filtered.length} of {rows.length}
            {settled ? ` · ${settled} settled` : ""}
          </span>
        }
      >
        <div className="flex flex-wrap items-center gap-3 py-4">
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
                className={`cursor-pointer transition-colors ${isOpen ? "bg-parchment/60" : "hover:bg-parchment/40"}`}
              >
                <Td>
                  <span className="block text-ink">{r.name}</span>
                  <span className="mt-0.5 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[0.75rem] text-faint">
                      {r.listing.agent_id}
                    </span>
                    {r.featured ? (
                      <span className="text-[0.75rem] text-muted">· featured</span>
                    ) : null}
                  </span>
                </Td>
                <Td className="text-muted">{r.vertical}</Td>
                <Td className="tnum text-muted">{r.preview.tenure_days}d</Td>
                <Td className="tnum">{r.preview.counts.total_records}</Td>
                <Td>
                  {r.preview.acp?.registered ? (
                    <span className="tnum text-closed">{r.preview.acp.completed_jobs}</span>
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                </Td>
                <Td className="tnum font-medium">${r.preview.valuation?.amount ?? "—"}</Td>
                <Td className="tnum text-muted">
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
      </Section>

      {detail ? <Detail row={detail} onOpen={() => onOpenListing(detail.listing.listing_id)} /> : null}
    </div>
  );
}

/**
 * What the seller asks against their own reference valuation.
 *
 * A real marketplace signal, and the reason the price is derived from the
 * valuation rather than typed: a seller asking 18% over is saying something,
 * and a seller asking under is saying something else.
 *
 * Rendered in plain ink with an explicit sign, not in red and green. The state
 * palette means one thing on this surface — escrow held, transfer closed,
 * refund triggered — and a listing priced above its reference valuation is
 * none of those. Colouring it red would say "something went wrong" about a
 * seller exercising ordinary judgement, and would spend the one signal that is
 * supposed to mean a refund.
 */
function Spread({ row }: { row: MarketRow }) {
  const valuation = Number(row.preview.valuation?.amount ?? 0);
  if (!valuation) return <span className="text-faint">—</span>;
  const ask = row.listing.price / 1_000_000;
  const pct = Math.round(((ask - valuation) / valuation) * 100);
  if (pct === 0) return <span className="tnum text-muted">at value</span>;
  return (
    <span className="tnum text-ink">
      {pct > 0 ? "+" : "−"}
      {Math.abs(pct)}%
    </span>
  );
}

function Detail({ row, onOpen }: { row: MarketRow; onOpen: () => void }) {
  const v = row.preview.valuation;
  return (
    <Section
      title={`${row.name} — valuation`}
      action={
        <button onClick={onOpen} className="text-[0.8125rem] underline underline-offset-4 hover:text-escrow">
          Open listing →
        </button>
      }
    >
      {v ? (
        <div className="mt-4">
          <Table head={["Factor", "Value", "Basis"]}>
            {v.factors.map((f) => (
              <tr key={f.name}>
                <Td className="text-muted">{f.name}</Td>
                <Td className="tnum">× {f.value}</Td>
                <Td className="text-muted">{f.explanation}</Td>
              </tr>
            ))}
          </Table>
          <p className="mt-3 text-[0.8125rem] text-muted">
            ${v.base_price} base × five factors = ${v.amount}
          </p>
        </div>
      ) : null}
      <FieldList className="mt-8">
        <Field label="Committed hash">
          <Hash value={row.listing.hash_commitment} chars={12} />
        </Field>
        <Field label="Categories">{row.listing.categories.join(", ")}</Field>
        <Field label="Memory size">{(row.preview.memory_size_bytes / 1024).toFixed(1)} KB</Field>
        <Field label="Counterparties">{row.preview.category_breakdown.relationship ?? 0}</Field>
        <Field label="Withheld">
          {row.preview.withheld_non_transferable} non-transferable, excluded before hashing
        </Field>
      </FieldList>
    </Section>
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
    <label className="flex items-center gap-2 text-[0.8125rem] text-muted">
      <span className="sr-only sm:not-sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-rule bg-vellum px-2.5 py-1.5 text-[0.8125rem] text-ink"
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
